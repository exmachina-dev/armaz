# -*- coding: utf-8 -*-

from drivers.AbstractDriver import AbstractDriver

from drivers.ModbusBackend import ModbusBackend

from drivers.Utils import retry


class ModbusDriverError(Exception):
    pass

class ModbusDriver(AbstractDriver):

    def __init__(self, config):

        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port"))
        self.target_nodeid = '.'.split(self.target_address)[-1]

        self.back = ModbusBackend(self.target_address, self.target_port,
                                  self.target_nodeid)

    @retry(ModbusDriverError, 5, 5, 2)
    def connect(self):
        if not self.back.connect():
            raise ModbusDriverError("Failed to connect %s:%i" % (self.target_address,
                                                                 self.target_port))
