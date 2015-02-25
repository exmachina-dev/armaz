# -*- coding: utf-8 -*-

from ertza.remotes.modbus import ModbusBackend
import ertza.errors as err


class ModbusMaster(object):
    def __init__(self, config, logger, restart_event, block_event,
            fake_master=False):
        self.config = config
        self.fake = fake_master
        if logger:
            self.lg = logger
        else:
            import logging
            self.lg = logging.getLogger()

        self.back = ModbusBackend(config, self.lg, restart_event, block_event)

    def start(self):
        if not self.fake:
            self.back.connect()

    def run(self):
        if not self.fake:
            self.back.get_status()
            self.back.get_command()

    def stop(self):
        if not self.fake:
            self.back.close()

    def restart(self):
        if not self.fake:
            self.back.reconnect()

