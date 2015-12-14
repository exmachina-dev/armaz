# -*- coding: utf-8 -*-

from ertza.commands.AbstractCommands import BufferedCommand
from ertza.commands.OscCommand import OscCommand


class DriveStatus(OscCommand, BufferedCommand):

    def execute(self, c):
        status = self.machine.driver['status']
        flat_status = list()
        for s in status:
            flat_status += s
        self.send(c.sender, '/drive/status', flat_status)

    @property
    def alias(self):
        return '/drive/status'


class DriveCommand(OscCommand, BufferedCommand):

    def execute(self, c):
        if len(c.args) != 2:
            self.send(c.sender, '/drive/command/error',
                      ('Invalid number of arguments for %s' % self.alias,),)

        try:
            k, v = c.args
            self.machine.driver['command'][k] = v
            self.ok(c)
        except Exception as e:
            self.error(c, (e,))

    @property
    def alias(self):
        return '/drive/command'
