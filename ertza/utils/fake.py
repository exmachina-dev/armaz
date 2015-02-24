# -*- coding: utf-8 -*-

from ..config import ConfigParser
from ..remotes.modbus import ModbusMaster


class FakeConfigParser(ConfigParser):
    def __init__(self):
        super(FakeConfigParser, self).__init__()

        self._conf_path = None
        self.save_path = None
        self.autosave = False
        self.read_hard_defaults()


class FakeModbusMaster(ModbusMaster):
    def __init__(self):
        cf = FakeConfigParser()
        super(FakeModbusMaster, self).__init__(cf, None, None, None)


class FakeConfig(object):
    def recv(self, *args):
        from ertza.config import ConfigResponse
        rp = ConfigResponse(self, self.rq, FakeConfigParser())

        rp.handle()
        rp.send()

        return rp

    def send(self, rq):
        self.rq = rq


class FakeModbus(object):
    def recv(self, *args):
        from ertza.remotes.modbus import ModbusResponse
        rp = ModbusResponse(self, self.rq, FakeModbusMaster())

        rp.handle()
        rp.send()

        return rp

    def send(self, rq):
        self.rq = rq
