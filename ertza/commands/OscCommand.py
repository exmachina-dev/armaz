# -*- coding: utf-8 -*-

import operator

from ertza.processors.osc.Osc import OscMessage
from .AbstractCommands import AbstractCommand


class OscCommand(AbstractCommand):

    @property
    def alias(self):
        return '/'

    def check_args(self, c, comp_op='eq', v=1):
        op = getattr(operator, comp_op)
        comp = op(len(c.args), v)
        if not comp:
            self.error(c, 'Invalid number of arguments for %s (%d %s %d: %s)' % (
                self.alias, len(c.args), comp_op, v, ' '.join(c.args)))

        return comp

    def send(self, target, path, *args, **kwargs):
        m = OscMessage(path, *args, receiver=target, **kwargs)
        self.machine.send_message(m)

    def ok(self, command, *args, **kwargs):
        self.send(command.sender, self.alias + '/ok', *args, **kwargs)

    def error(self, command, *args, **kwargs):
        args = [str(a) if isinstance(a, Exception) else a for a in args]
        self.send(command.sender, self.alias + '/error', *args, **kwargs)

    def reply(self, command, *args, **kwargs):
        self.send(command.sender, self.alias, *args, **kwargs)
