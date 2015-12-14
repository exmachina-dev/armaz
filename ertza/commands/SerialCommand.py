# -*- coding: utf-8 -*-

from ertza.processors.serial.Serial import SerialMessage
from .AbstractCommands import AbstractCommand


class SerialCommand(AbstractCommand):
    @property
    def alias(self):
        # This fix a bug:
        # Processor seems to include this class while loading modules…
        return ':'

    def send(self, *args, **kwargs):
        m = kwargs['msg'] if 'msg' in kwargs else \
            SerialMessage()

        for d in args:
            m.cmd_bytes['data'] += d

        self.machine.send_message(m)

    def ok(self, command, *args, **kwargs):
        self.send(self.alias + ':ok', **kwargs)

    def error(self, command, *args, **kwargs):
        self.send(self.alias + ':error', **kwargs)
