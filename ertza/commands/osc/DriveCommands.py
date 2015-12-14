# -*- coding: utf-8 -*-

from ertza.commands.AbstractCommands import BufferedCommand
from ertza.commands.OscCommand import OscCommand


class DriveStatus(OscCommand, BufferedCommand):

    def execute(self, c):
        status = self.machine.driver['status']
        self.send(c.sender, '/drive/status', status)
