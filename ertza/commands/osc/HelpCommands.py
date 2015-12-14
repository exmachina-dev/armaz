# -*- coding: utf-8 -*-

from ertza.commands.AbstractCommands import UnbufferedCommand
from ertza.commands.OscCommand import OscCommand

from ertza.processors.osc.Osc import OscMessage


class ListCommands(OscCommand, UnbufferedCommand):

    def execute(self, c):
        cmds = self.machine.osc_processor.available_commands
        reply_path = '/help/implemented_osc_commands'
        for cmd in cmds:
            self.send(c.sender, reply_path, cmd)

    @property
    def alias(self):
        return '/help/list'
