# -*- coding: utf-8 -*-

from ertza.commands.AbstractCommands import UnbufferedCommand
from ertza.commands.OscCommand import OscCommand

from ertza.Osc import OscMessage


class DriveStatus(OscCommand):

    def execute(self, c):
        msg = OscMessage('/drive/status', ('ok',), receiver=c.sender)
        self.machine.send_message(c.protocol, msg)


class ListCommands(OscCommand, UnbufferedCommand):

    def execute(self, c):
        cmds = self.machine.osc_processor.available_commands
        reply_path = '/help/implemented_osc_commands'
        for cmd in cmds:
            msg = OscMessage(reply_path, cmd, receiver=c.sender)
            self.machine.send_message(c.protocol, msg)

    def get_description(self):
        return "List all implemented G-codes"

    def get_long_description(self):
        return ("Lists all the G-codes implemented by this firmware. "
                "To get a long description of each code use '?' "
                "after the code name, for instance, G0? will give a long decription of G0")

    @property
    def alias(self):
        return '/help'
