# -*- coding: utf-8 -*-

import liblo as lo
import logging
from datetime import datetime
from threading import Thread
from threading import Event
from queue import Queue, Empty

from ertza.drivers.AbstractDriver import AbstractDriver, AbstractDriverError
from ertza.processors.osc.Osc import OscAddress, OscMessage


class OscDriverError(AbstractDriverError):
    pass


class OscDriverTimeout(OscDriverError):
    pass


class OscDriver(AbstractDriver):

    def __init__(self, config, machine):
        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port"))
        self.target = OscAddress(hostname=self.target_address,
                                 port=self.target_port)

        self.machine = machine

        self.outlet, self.inlet = None, None
        self.osc_pipe = None
        self.running = Event()
        self.timeout = 5.0

        self._waiting_futures = []

    def init_queue(self):
        self.queue = Queue(maxsize=10)

        return self.queue

    def connect(self):
        self._thread = Thread(target=self.from_machine)
        self._thread.daemon = True
        self._thread.start()

    def register(self):
        try:
            sn = self.machine.serialnumber if self.machine.serialnumber \
                else False
            if sn:
                m = self.message('/slave/register', sn, types='s')
            else:
                m = self.message('/slave/register', sn, types='F')

            self.to_machine(m)
        except AbstractDriverError as e:
            logging.exception('Error while registering: %s' % str(e))

    def exit(self):
        self['command:stop'] = True
        self['command:enable'] = False

        self.send_to_slave('free', self.machine.serialnumber)
        self.running.set()

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self.target, **kwargs)

    def ping(self):
        m = self.message('/slave/ping')
        t = datetime.now().timestamp()
        fut = self.to_machine(m, m.path)
        reply = None
        try:
            reply = self.wait_for_future(fut)
            reply += t
            return reply
        except OscDriverTimeout as e:
            logging.error(e)
            return reply, e

    def to_machine(self, request, uid=None):
        try:
            if not uid:
                uid = ' '.join((request.path, request.args[0]))
            event = Event()
            future = OscFutureResult(uid)
            future.set_callback(self.done_cb)
            future.set_event(event)
            self._waiting_futures.append(future)
            logging.debug(self._waiting_futures)
            self._send(request)
            return future
        except:
            raise

    def from_machine(self):
        while not self.running.is_set():
            try:
                recv_item = self.queue.get(block=True)
                logging.debug('Received %s in slave loop' % repr(recv_item))

                f_id = None
                for i, f in enumerate(self._waiting_futures):
                    if recv_item == f:
                        f_id = i
                        logging.debug(f_id)
                        break
                if f_id is None:
                    logging.error('Unable to find waiting future '
                                  'for %s' % str(f))
                    continue
                future = self._waiting_futures.pop(f_id)
                if self._check_error(recv_item):
                    future.set_result(OscDriverError(str(recv_item)))
                else:
                    future.set_result(recv_item)

                self.queue.task_done()
            except OscDriverError as e:
                logging.exception('Exception in %s: %s' % (self.__class__.__name__,
                                                           repr(e)))

    def done_cb(self, *args):
        logging.debug(' '.join([str(i) for i in args]))

    def wait_for_future(self, fut):
        if fut.event.wait(self.timeout):
            return fut.result
        raise OscDriverTimeout('Timeout')

    def __getitem__(self, key):
        m = self.message('/slave/get', key)
        fut = self.to_machine(m)
        ret = self.wait_for_future(fut)

        return ret

    def __setitem__(self, key, *args):
        m = self.message('/slave/set', key, *args)
        fut = self.to_machine(m)
        ret = self.wait_for_future(fut)

        return ret

    def _send(self, message, *args, **kwargs):
        try:
            m = message
            m.receiver = self.target
            lo.send((m.receiver.hostname, m.receiver.port), m.message)
        except OSError as e:
            raise OscDriverError(str(e))

    def _check_error(self, command):
        if command.path.endswith('/error'):
            return True


class OscFutureResult(object):
    def __init__(self, uid):
        self._callback = None
        self._result = None
        self._event = None
        self._uid = uid

    def set_callback(self, cb):
        if self._callback:
            raise ValueError('Callback is already defined')
        self._callback = cb

    def set_event(self, event):
        if self._event:
            raise ValueError('Event is already defined')
        self._event = event

    @property
    def event(self):
        if not self._event:
            raise ValueError('Event is not defined')
        return self._event

    def set_result(self, result):
        if self._result is not None:
            raise ValueError('Result is already defined')
        self._result = result
        self.event.set()
        if isinstance(self.result, Exception):
            raise self.result

        if self._callback:
            self._callback(self)

    @property
    def result(self):
        if not self._result:
            raise ValueError('Result is not yet defined')
        return self._result

    def __eq__(self, other):
        try:
            if self.uid == other.uid:
                return True
            return False
        except AttributeError as e:
            raise TypeError('%s is not comparable with %s: %s' % (
                self.__class__.__name__, other.__class__.__name__, str(e)))

    @property
    def uid(self):
        if not self._result:
            return self._uid
        clean_path = self.result.path.replace('/ok', '', 1).replace('/error', '', 1)
        if '/ping' in clean_path:
            return clean_path
        key_arg = self.result.args[0]
        uid = ' '.join((clean_path, key_arg,))
        return uid
