# -*- coding: utf-8 -*-

from ertza.remotes.modbus import ModbusBackend
import ertza.errors as err


class ModbusMaster(object):
    def __init__(self, config, logger, restart_event, block_event, **kwargs):
        self.config = config

        if logger:
            self.lg = logger
        else:
            import logging
            self.lg = logging.getLogger()

        self.fake = False
        if 'without_modbus' in kwargs:
            self.fake = kwargs['without_modbus']
            if self.fake:
                self.lg.warn('Starting modbus master in fake mode.')

        if 'direct_enslave' in kwargs and kwargs['direct_enslave'] is True:
            kwargs['slave'] = '192.168.100.3'

        self.back = ModbusBackend(config, self.lg, restart_event, block_event,
                **kwargs)

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

