# -*- coding: utf-8 -*-

from ertza.remotes.modbus import ModbusBackend
import ertza.errors as err


class ModbusMaster(object):
    def __init__(self, config, logger, restart_event, block_event):
        self.config = config
        if logger:
            self.lg = logger
        else:
            import logging
            self.lg = logging.getLogger()

        self.back = ModbusBackend(config, self.lg, restart_event, block_event)

    def start(self):
        self.back.connect()

    def run(self):
        self.back.get_status()
        self.back.get_command()

    def stop(self):
        self.back.close()

    def restart(self):
        self.back.reconnect()

