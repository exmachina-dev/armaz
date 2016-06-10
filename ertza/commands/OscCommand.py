# -*- coding: utf-8 -*-

from ertza.processors.osc.Osc import OscMessage
from .AbstractCommands import AbstractCommand


class OscCommand(AbstractCommand):
    def send(self, target, path, *args, **kwargs):
        if args and isinstance(args[0], (list, tuple)):
            args = args[0]

        m = OscMessage(path, *args, receiver=target, **kwargs)
        self.machine.send_message(m)

    def ok(self, command, *args, **kwargs):
        self.send(command.sender, self.alias + '/ok', *args, **kwargs)

    def error(self, command, *args, **kwargs):
        args = [str(a) if isinstance(a, Exception) else a for a in args]
        self.send(command.sender, self.alias + '/error', *args, **kwargs)

    def reply(self, command, *args, **kwargs):
        self.send(command.sender, self.alias, *args, **kwargs)
