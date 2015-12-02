# -*- coding: utf-8 -*-

from drivers.AbstractDriver import AbstractDriver

from drivers.ModbusBackend import ModbusBackend


class ModbusDriver(AbstractDriver):

    def __init__(self, config):

        self.target_address = config.get("target_address")
        self.target_port = config.get("target_port")
        self.target_nodeid = '.'.split(self.target_address)[-1]

        self.back = ModbusBackend(self.target_address, self.target_port,
                                  self.target_nodeid)

    def connect(self):

        self.back.connect()
