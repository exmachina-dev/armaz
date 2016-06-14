# -*- coding: utf-8 -*-

from ertza.commands import UnbufferedCommand
from ertza.commands import OscCommand


class ListCommands(OscCommand, UnbufferedCommand):

    def execute(self, c):
        cmds = self.machine.processors['OSC'].available_commands
        for cmd in cmds:
            if hasattr(cmd, 'help_text'):
                self.reply(c, cmd, cmd.help_text)
            else:
                self.reply(c, cmd)

        self.reply(c, 'done')

    @property
    def alias(self):
        return '/help/list'
