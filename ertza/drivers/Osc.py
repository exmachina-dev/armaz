# -*- coding: utf-8 -*-

import liblo as lo
import logging
import asyncio
import functools
from datetime import datetime
from multiprocessing import Pipe, Event

from ertza.drivers.AbstractDriver import AbstractDriver, AbstractDriverError
from ertza.processors.osc.Osc import OscAddress, OscMessage
from ertza.drivers.Utils import coroutine


class OscDriverError(AbstractDriverError):
    pass


class OscDriverTimeout(OscDriverError):
    pass


class OscDriver(AbstractDriver):

    _loop = asyncio.get_event_loop()
    _loop.set_debug(True)

    def __init__(self, config, machine):
        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port"))
        self.target = OscAddress(hostname=self.target_address,
                                 port=self.target_port)

        self.machine = machine

        self.outlet, self.inlet = None, None
        self.osc_pipe = None
        self.running = False
        self.timeout = 2.0

    def init_pipe(self):
        self.outlet, self.inlet = Pipe(False)

        return self.inlet

    def connect(self):
        try:
            self.running = True
            self.osc_pipe = self._pipe_coroutine()
            sn = self.machine.serialnumber if self.machine.serialnumber \
                else 'No S/N'
            # m = self.message('/slave/register', sn, types='s')
            # self.to_machine(m)
        except AbstractDriverError as e:
            logging.exception('Error while registering: %s' % str(e))

        return self

    def exit(self):
        self['command:stop'] = True
        self['command:enable'] = False

        self.send_to_slave('free', self.machine.serialnumber)
        self.running = False

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self.target, **kwargs)

    def ping(self):
        m = self.message('/slave/ping')
        t = datetime.now()
        ev, res = self.to_machine(m)
        if ev.wait(self.timeout):
            return res.result()
        raise OscDriverTimeout()

    @asyncio.coroutine
    def to_machine(self, request):
        try:
            fut = asyncio.Future()
            event = Event()
            done_cb = functools.partial(self.done_cb, event)
            fut.add_done_callback(done_cb)
            self._send(request)
            yield from asyncio.wait_for(
                self.from_machine(fut), self.timeout)
            return event, fut

        except StopIteration:
            return ()
        except:
            raise

    @asyncio.coroutine
    def from_machine(self, future):
        res = yield from self.outlet.recv()
        future.set_result(res)

    def done_cb(self, event, fut):
        event.set()
        logging.debug(fut.result())

    def __getitem__(self, key):
        m = self.message('/slave/get', key)
        for ret in self.to_machine(m):
            return ret
        raise OscDriverError('No reply')

    def __setitem__(self, key, value):
        m = self.message('/slave/set', key, value)
        ret = self.to_machine(m)

        if ret['key'] == key:
            return ret['value']
        raise OscDriverError('Unexpected reply')

    @asyncio.coroutine
    def _pipe_listener(self):
        while self.running:
            yield self.outlet.recv()

    @asyncio.coroutine
    def _pipe_coroutine(self):
        if self.outlet:
            response = None
            while self.running:
                try:
                    request = (yield response)
                    try:
                        self._send(request)
                    except Exception as e:
                        logging.error('Error while sending: %s' % str(e))

                    yield from self._pipe_listener()
                except Exception as e:
                    raise OscDriverError('Exception while receiving: %s' % str(e))
        else:
            raise OscDriverError('No queue initialized')

    def _send(self, message, *args, **kwargs):
        try:
            m = message
            m.receiver = self.target
            lo.send((m.receiver.hostname, m.receiver.port), m.message)
        except OSError as e:
            raise OscDriverError(str(e))
