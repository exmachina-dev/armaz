# -*- coding: utf-8 -*-

import liblo as lo
from queue import Empty

from ertza.drivers.AbstractDriver import AbstractDriver, AbstractDriverError

from ertza.processors.osc.Osc import OscAddress, OscMessage


class OscDriverError(AbstractDriverError):
    pass


class OscDriver(AbstractDriver):

    def __init__(self, config, machine):
        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port"))
        self.target = OscAddress(hostname=self.target_address,
                                 port=self.target_port)

        self.machine = machine

        self.in_queue = None
        self.timeout = 2

    def connect(self):
        self.send_to_slave('register', self.machine.serialnumber)

    def exit(self):
        self['command:stop'] = True
        self['command:enable'] = False

        self.send_to_slave('free', self.machine.serialnumber)

    def send_to_slave(self, path, *args, **kwargs):
        m = OscMessage('/slave/%s' % path, *args, **kwargs)
        m.receiver = self.target
        om = lo.Message(m.path, *m.args)
        lo.send((m.receiver.hostname, m.receiver.port), om)

    def __getitem__(self, key):
        self.send_to_slave('get', key)
        return self._wait_for_reply()

        ret = self._wait_for_reply()
        if ret['key'] == key:
            return ret['value']
        raise OscDriverError('Unexpected reply')

    def __setitem__(self, key, value):
        self.send_to_slave('set', key, value)

        ret = self._wait_for_reply()
        if ret['key'] == key:
            return ret['value']
        raise OscDriverError('Unexpected reply')

    def _wait_for_reply(self):
        if self.in_queue:
            try:
                ret = self.in_queue.get(block=True, timeout=self.timeout)
                return ret
            except Empty:
                raise OscDriverError('Timeout')
