# -*- coding: utf-8 -*-

import logging

from ertza.commands.AbstractCommands import UnbufferedCommand
from ertza.commands.OscCommand import OscCommand

from ertza.processors.osc.Osc import OscMessage, OscAddress


class OscLogHandler(logging.Handler):

    def __init__(self, machine, target):
        self.machine = machine
        self._target = OscAddress(hostname=target)

        super().__init__()

    def emit(self, record):
        try:
            self.send(self._target, '/log/entry', (self.format(record),),
                      msg_type='log')
        except Exception:   # This a log handler, we forgive everything
            pass


class LogTo(OscCommand, UnbufferedCommand):

    def execute(self, c):
        log_trg = c.args[0]
        self.machine.osc_loghandler = OscLogHandler(self.machine, log_trg)
        root_log = logging.getLogger()
        root_log.addHandler(self.machine.osc_loghandler)
        self.send(c.sender, '/log/info',
                  ('Binding OSC log handler to %s' % log_trg,),)

    @property
    def alias(self):
        return '/log/to'


class LogLevel(OscCommand, UnbufferedCommand):

    def execute(self, c):
        try:
            self.machine.osc_loghandler.setLevel(c.args[0])
        except AttributeError:
            self.send(c.sender, '/log/error', 'OSC log handler is not specified. '
                      'Run /log/to target prior to this command',)

    @property
    def alias(self):
        return '/log/level'
