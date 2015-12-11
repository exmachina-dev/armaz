# -*- coding: utf-8 -*-

from ertza.commands.AbstractCommands import BufferedCommand
from ertza.commands.OscCommand import OscCommand

from ertza.processor.Osc import OscMessage


class DriveStatus(OscCommand, BufferedCommand):

    def execute(self, c):
        msg = OscMessage('/drive/status', ('ok',), receiver=c.sender)
        self.machine.send_message(c.protocol, msg)
