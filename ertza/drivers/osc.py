# -*- coding: utf-8 -*-

import liblo as lo
import logging
from threading import Thread
from threading import Event
from threading import Timer
from queue import Queue
import uuid

from .abstract_driver import AbstractDriver, AbstractDriverError, AbstractTimeoutError
from ..machine.slave import SlaveRequest
from ..processors.osc import OscAddress, OscMessage

from ..async_utils import coroutine

logging = logging.getLogger('ertza.driver.osc')


class OscDriverError(AbstractDriverError):
    pass


class OscDriverTimeout(OscDriverError, AbstractTimeoutError):
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
        self.running_event = Event()
        self.timeout = config.get('timeout', 0.25)

        self._waiting_futures = {}
        self._timeout_timers = {}
        self.timeout_event = Event()

    def init_pipes(self):
        self.outlet = self.gen_future(self._send(), self.gen_timeout_timer())
        self.inlet = self.inlet_pipe()

    def connect(self):
        self.init_pipes()

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

        self.running_event.set()

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self.target, **kwargs)

    def ping(self):
        rq = SlaveRequest(ping=True, block=True)
        reply = None
        try:
            reply = self.wait_for_reply(rq)
            return reply
        except OscDriverTimeout as e:
            logging.error(e)
            return reply, e

    @coroutine
    def gen_future(self, *outlet_coros):
        while not self.running_event.is_set():
            request = (yield)
            if not isinstance(request, SlaveRequest):
                raise TypeError('Wrong request type: {!s}'.format(type(request)))

            try:
                if not request.uuid:
                    request.uuid = uuid.uuid4().hex

                if not request.event:
                    request.event = Event()

                future = OscFutureResult(request)
                request.callback = self.done_cb
                self._waiting_futures[request.uuid] = future
                for outlet_coro in outlet_coros:
                    outlet_coro.send(request)
            except:
                raise

    @coroutine
    def gen_timeout_timer(self):
        while not self.running_event.is_set():
            request = (yield)
            if not isinstance(request, SlaveRequest):
                raise TypeError('Wrong request type: {!s}'.format(type(request)))

            try:
                if not request.uuid:
                    request.uuid = uuid.uuid4().hex

                timer = Timer(self.timeout, self.timeout_cb, args=(request,))
                timer.start()
                self._timeout_timers[request.uuid] = timer
            except:
                raise

    @coroutine
    def inlet_pipe(self):
        while not self.running_event.is_set():
            try:
                message = (yield)

                future = self._waiting_futures.pop(message.uuid, None)
                timer = self._timeout_timers.pop(message.uuid, None)

                if timer:
                    timer.cancel()

                if future is None:
                    logging.error('Unable to find waiting future '
                                  'for {!s}'.format(message.uuid))
                    continue

                future.request.reply = message
                if self._check_error(message):
                    future.request.exception = OscDriverError(str(message))
            except OscDriverTimeout as e:
                logging.error('Timeout in %s: %s' % (self.__class__.__name__,
                                                     repr(e)))
            except OscDriverError as e:
                logging.error('Exception in %s: %s' % (self.__class__.__name__,
                                                       repr(e)))

    def done_cb(self, *args):
        pass

    def timeout_cb(self, request):
        self.timeout_event.set()
        logging.error('Timeout for request {!s}'.format(request))

    def wait_for_reply(self, request):
        if request.event.wait(self.timeout):
            return request.reply
        raise OscDriverTimeout('Timeout while waiting for {!s}'.format(request))

    def __getitem__(self, key):
        rq = SlaveRequest(key, getitem=True)
        self.outlet.send(rq)
        try:
            ret = self.wait_for_reply(rq)
            return ret
        except OscDriverTimeout as e:
            logging.error(e)
            raise e
        except OscDriverError as e:
            logging.error(e)

    def __setitem__(self, key, *args):
        rq = SlaveRequest(*args, setitem=True)
        self.outlet.send(rq)

        try:
            ret = self.wait_for_reply(rq)
            return ret
        except OscDriverTimeout as e:
            logging.error(e)
            raise e
        except OscDriverError as e:
            logging.error(e)

    @coroutine
    def _send(self):
        while not self.running_event.is_set():
            request = (yield)
            try:
                path = request.kwargs.get('path', None)

                if path is None:
                    if request.getitem:
                        path = '/slave/get'
                    elif request.setitem:
                        path = '/slave/set'
                    elif request.ping:
                        path = '/slave/ping'

                    raise ValueError('Unable to guess path from request')

                m = self.message(path, request.uid, *request.args)
                m.receiver = self.target
                lo.send((m.receiver.hostname, m.receiver.port), m.message)
            except OSError as e:
                raise OscDriverError(str(e))

    def _check_error(self, command):
        if command.path.endswith('/error'):
            return True


class OscFutureResult(object):
    def __init__(self, request):
        self._request = request

    def __eq__(self, other):
        try:
            if self.uuid == other.uuid:
                return True
            return False
        except AttributeError as e:
            raise TypeError('%s is not comparable with %s: %s' % (
                self.__class__.__name__, other.__class__.__name__, str(e)))

    @property
    def uuid(self):
        return self._request.uuid

    def __repr__(self):
        return 'WF {}'.format(self.uid)
