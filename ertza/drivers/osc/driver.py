# -*- coding: utf-8 -*-

import liblo as lo
import logging
from threading import Event
from threading import Timer
import uuid

from .utils import OscFutureResult
from .errors import OscDriverError, OscDriverTimeout
from ..abstract_driver import AbstractDriver, AbstractDriverError
from ...machine.slave import SlaveRequest
from ...processors.osc import OscAddress, OscMessage

from ...async_utils import coroutine

logging = logging.getLogger('ertza.driver.osc')


class OscDriver(AbstractDriver):

    def __init__(self, config, machine):
        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port"))
        self.target = OscAddress(hostname=self.target_address,
                                 port=self.target_port)

        self.machine = machine

        self.outlet, self.inlet = None, None
        self.timeout = config.get('timeout', 0.5)

        self._waiting_futures = {}
        self._timeout_timers = {}

        self.running_event = Event()
        self.timeout_event = Event()
        self.fault_event = Event()

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
        self.set('machine:command:stop', True, block=True)
        self.set('machine:command:enable', False, block=True)

        self.running_event.set()

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self.target, **kwargs)

    def ping(self, **kwargs):
        rq = SlaveRequest(ping=True, **kwargs)
        self.outlet.send(rq)

        if kwargs.get('block', True):
            return self.wait_for_reply(rq)
        else:
            return rq

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

                if message.path.endswith('/error'):
                    future.request.exception = OscDriverError(str(message))

                future.request.reply = message

            except OscDriverTimeout as e:
                logging.error('Timeout in %s: %s' % (self.__class__.__name__,
                                                     repr(e)))
            except OscDriverError as e:
                logging.error('Exception in %s: %s' % (self.__class__.__name__,
                                                       repr(e)))

    def done_cb(self, *args):
        pass

    def timeout_cb(self, request):
        request.kwargs['exception'] = OscDriverTimeout('Timeout for {!s}'.format(request))
        request.kwargs['timeout'] = True
        self.timeout_event.set()
        logging.error('Timeout for request {!s}'.format(request))
        self._timeout_timers.pop(request.uuid, None)
        orphan_future = self._waiting_futures.pop(request.uuid, None)
        if orphan_future:
            logging.error('Removed orphan future: {!s}'.format(orphan_future))

    def wait_for_reply(self, request):
        if request.event is None:
            raise OscDriverError('Cannot wait for reply, no event specified')

        if request.event.wait(self.timeout):
            return request.reply
        raise OscDriverTimeout('Timeout while waiting for {!s}'.format(request))

    def get(self, key, **kwargs):
        block = kwargs.get('block', False)
        try:
            rq = SlaveRequest(key, getitem=True, **kwargs)
            self.outlet.send(rq)

            if block:
                return self.wait_for_reply(rq)

        except OscDriverTimeout as e:
            logging.error(e)
            raise
        except OscDriverError as e:
            logging.error(e)

    def set(self, key, *args, **kwargs):
        block = kwargs.get('block', False)
        try:
            rq = SlaveRequest(key, *args, setitem=True, **kwargs)
            self.outlet.send(rq)

            if block:
                return self.wait_for_reply(rq)

        except OscDriverTimeout as e:
            logging.error(e)
            raise
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
                    else:
                        raise ValueError('Unable to guess path from request')

                m = self.message(path, request.uuid, *request.args)
                m.receiver = self.target
                lo.send((m.receiver.hostname, m.receiver.port), m.message)
            except OSError as e:
                raise OscDriverError(str(e))

    def __getitem__(self, key):
        return self.get(key, block=True)

    def __setitem__(self, key, *args):
        return self.set(key, *args, block=True)
