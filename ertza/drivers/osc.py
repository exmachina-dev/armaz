# -*- coding: utf-8 -*-

import liblo as lo
import logging
from threading import Thread
from threading import Event
from queue import Queue
import uuid
import asyncoro as asc

from .abstract_driver import AbstractDriver, AbstractDriverError, AbstractTimeoutError
from ..processors.osc import OscAddress, OscMessage

logging = logging.getLogger('ertza.driver.osc')


class OscDriverError(AbstractDriverError):
    pass


class OscDriverTimeout(OscDriverError, AbstractTimeoutError):
    pass


class _OscRequest(object):
    __slots__ = ('path', 'args', 'reply', 'exception', 'uuid', 'timeout')

    def __init__(self, path, *args, **kwargs):
        self.path = path
        self.args = args
        self.reply = None
        self.uuid = None
        self.timeout = None
        self.exception = None

    def __getstate__(self):
        st = {'path': self.path, 'args': self.args, 'reply': self.reply,
              'uuid': self.uuid, 'timeout': self.timeout,
              'exception': self.exception}
        return st

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)


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
        self.timeout = config.get('timeout', 0.25)

        self._waiting_reqs = {}

        self.slave_channel = asc.Channel('{0.target_address}:{0.target_port}'.format(self))

    def init_queue(self):
        self.queue = Queue(maxsize=45)

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
        self['machine:command:stop'] = True
        self['machine:command:enable'] = False

        self.running.set()

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self.target, **kwargs)

    def ping(self):
        m = self.message('/slave/ping')
        fut = self.to_machine(m)
        reply = None
        try:
            reply = self.wait_for_future(fut)
            return reply
        except OscDriverTimeout as e:
            logging.error(e)
            return reply, e

    def to_machine(self, coro=None):
        try:
            request = yield coro.receive()
            if not isinstance(request, _OscRequest):
                raise TypeError('Unexpected request type: {}'.format(type(request)))

            if not request.uuid:
                request.uuid = uuid.uuid4().hex
            request.event = asc.Event()
            future = OscFutureResult(uuid)
            future.callback = self.done_cb
            future.event = request.event
            request.future = future
            self._waiting_reqs[request.uuid] = request
            yield coro.send(request)
        except:
            raise

    def from_machine(self, coro=None):
        while not self.running.is_set():
            try:
                recv_item = yield coro.receive()

                if recv_item.uuid not in self._waiting_reqs:
                    logging.error('Unable to find waiting future '
                                  'for %s' % str(recv_item.uuid))
                    continue

                areq = self._waiting_reqs.pop(recv_item.uuid)

                if self._check_error(recv_item):
                    areq.reply = recv_item
                    areq.exception = OscDriverError(str(recv_item))
                else:
                    areq.reply = recv_item

            except OscDriverTimeout as e:
                logging.error('Timeout in %s: %s' % (self.__class__.__name__,
                                                     repr(e)))
            except OscDriverError as e:
                logging.error('Exception in %s: %s' % (self.__class__.__name__,
                                                       repr(e)))

    def done_cb(self, *args):
        pass

    def wait_for_future(self, req):
        fut = req.future
        if fut.event.wait(self.timeout):
            return fut.result
        raise OscDriverTimeout('Timeout while waiting for %s' % repr(fut))

    def __getitem__(self, key):
        m = self.message('/slave/get', key)
        fut = self.to_machine(m)
        try:
            ret = self.wait_for_future(fut)
            return ret
        except OscDriverTimeout as e:
            logging.error(e)
            raise e
        except OscDriverError as e:
            logging.error(e)

    def __setitem__(self, key, *args):
        m = self.message('/slave/set', key, *args)
        fut = self.to_machine(m)
        try:
            ret = self.wait_for_future(fut)
            return ret
        except OscDriverTimeout as e:
            logging.error(e)
            raise e
        except OscDriverError as e:
            logging.error(e)

    def _send(self, coro=None):
        try:
            rq = yield coro.receive()
            m = self.message(rq.path, rq.uid, *rq.args)
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
        self._exception = None
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
        if isinstance(self.result, (list, tuple)):
            self._exception = self.result[1]

        if self._callback:
            self._callback(self)

    @property
    def result(self):
        if self._exception:
            raise self._exception
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
        return self._uid

    def __repr__(self):
        return 'WF {}'.format(self.uid)
