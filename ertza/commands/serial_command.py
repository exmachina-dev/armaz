# -*- coding: utf-8 -*-

from ..processors.serial import SerialMessage
from .abstract_commands import AbstractCommand


class SerialCommand(AbstractCommand):
    SEP = '.'

    def send(self, *args, **kwargs):
        m = kwargs['msg'] if 'msg' in kwargs else \
            SerialMessage()

        for d in args:
            m.cmd_bytes += d

        return self.machine.send_message(m)

    def ok(self, command, *args, **kwargs):
        self.reply(command, *args, add_path='.ok', **kwargs)

    def error(self, command, *args, **kwargs):
        self.reply(command, *args, add_path='.error', **kwargs)

    def reply(self, command, *args, **kwargs):
        add_path = kwargs.pop('add_path', None)
        if add_path:
            if not isinstance(add_path, str):
                raise TypeError('add_path kwarg must be a string')
            full_path = self.alias + add_path if add_path.startswith(self.SEP) \
                else '{0.alias}{0.SEP}{1}'.format(self, add_path)
        else:
            full_path = self.alias

        self.send(command.sender, full_path, *args, **kwargs)
