# -*- coding: utf-8 -*-

from ..processors.serial import SerialMessage
from .AbstractCommands import AbstractCommand


class SerialCommand(AbstractCommand):
    def send(self, *args, **kwargs):
        m = kwargs['msg'] if 'msg' in kwargs else \
            SerialMessage()

        for d in args:
            m.cmd_bytes += d

        self.machine.send_message(m)

    def ok(self, command, *args, **kwargs):
        self.send(self.alias + '.ok', *args, **kwargs)

    def reply(self, command, *args, **kwargs):
        self.send(self.alias + '.reply', *args, **kwargs)

    def error(self, command, *args, **kwargs):
        self.send(self.alias + '.error', *args, **kwargs)
