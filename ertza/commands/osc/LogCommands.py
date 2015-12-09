# -*- coding: utf-8 -*-

import logging

from ertza.commands.AbstractCommands import UnbufferedCommand
from ertza.commands.OscCommand import OscCommand

from ertza.Osc import OscMessage, OscAddress


class OscLogHandler(logging.Handler):

    def __init__(self, machine, target):
        self.machine = machine
        self._target = OscAddress(target)

        super().__init__()

    def emit(self, record):
        msg = OscMessage('/log/entry', self.format(record),
                         receiver=self._target)
        self.machine.send_message('OSC', msg)


class LogTo(OscCommand, UnbufferedCommand):

    def execute(self, c):
        log_trg = c.args[0]
        msg = OscMessage('/log/info', 'Binding OSC log handler to %s' % log_trg,
                         receiver=c.sender)
        self.machine.osc_loghandler = OscLogHandler(log_trg)
        self.machine.send_message(c.protocol, msg)

    @property
    def alias(self):
        return '/log/to'


class LogLevel(OscCommand, UnbufferedCommand):

    def execute(self, c):
        try:
            self.machine.osc_loghandler.setLevel(c.args[0])
        except AttributeError:
            msg = OscMessage('/log/error', 'OSC log handler is not specified. '
                             'Run /log/to target prior to this command',
                             receiver=c.sender)
            self.machine.send_message(c.protocol, msg)

    @property
    def alias(self):
        return '/log/level'
