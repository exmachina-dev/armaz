# -*- coding: utf-8 -*-

import liblo as lo
import logging
from datetime import datetime
from multiprocessing import Pipe

from ertza.drivers.AbstractDriver import AbstractDriver, AbstractDriverError
from ertza.processors.osc.Osc import OscAddress, OscMessage
from ertza.drivers.Utils import coroutine


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
        self.running = False
        self.timeout = 2.0

    def init_pipe(self):
        self.outlet, self.inlet = Pipe(False)

        return self.inlet

    def connect(self):
        try:
            self.running = True
            self.osc_pipe = self._pipe_coroutine()
            m = self.message('/slave/register', self.machine.serialnumber)
            self.osc_pipe.send(m)
        except AbstractDriverError as e:
            pass

    def exit(self):
        self['command:stop'] = True
        self['command:enable'] = False

        self.send_to_slave('free', self.machine.serialnumber)
        self.running = False

    def message(self, *args, **kwargs):
        return OscMessage(*args, receiver=self.target, **kwargs)

    def _send(self, path, *args, **kwargs):
        try:
            m = OscMessage('/slave/%s' % path, *args, **kwargs)
            m.receiver = self.target
            om = lo.Message(m.path, *m.args)
            lo.send((m.receiver.hostname, m.receiver.port), om)
        except OSError as e:
            raise OscDriverError(str(e))

    def ping(self):
        m = self.message('/slave/ping')
        t = datetime.now()
        res = self.to_machine(m)
        for r in res:
            return res, (datetime.now() - t).total_seconds()
        raise OscDriverError('No reply')


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

    @coroutine
    def _pipe_coroutine(self):
        if self.outlet:
            response = None
            while self.running:
                try:
                    request = (yield response)
                    try:
                        self._send(request)
                    except:
                        pass
                    if self.outlet.poll(self.timeout):
                        response = self.outlet.recv()
                    else:
                        raise OscDriverTimeout('Timeout')
                except Exception as e:
                    raise OscDriverError('Exception while receiving: %s' % str(e))
        else:
            raise OscDriverError('No queue initialized')

    def to_machine(self, request):
        try:
            return self.osc_pipe.send(request)
        except StopIteration:
            return ()
        except:
            raise
