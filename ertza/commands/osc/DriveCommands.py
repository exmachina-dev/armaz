# -*- coding: utf-8 -*-

from ertza.commands.AbstractCommands import BufferedCommand
from ertza.commands.OscCommand import OscCommand


class DriveStatus(OscCommand, BufferedCommand):

    def execute(self, c):
        status = self.machine.driver['status']
        flat_status = list()
        for s in status:
            flat_status += s
        self.send(c.sender, '/drive/status', *flat_status)

    @property
    def alias(self):
        return '/drive/status'


class DriveCommand(OscCommand, BufferedCommand):

    def execute(self, c):
        if len(c.args) != 2:
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            k, v = c.args
            self.machine.driver['command:%s' % k] = v
            self.ok(c)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/drive/command'


class DriveSet(OscCommand, BufferedCommand):

    def execute(self, c):
        if len(c.args) < 2:
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            k, v, = c.args
            self.machine.driver[k] = v
            self.ok(c)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/drive/set'


class DriveGet(OscCommand, BufferedCommand):

    def execute(self, c):
        if len(c.args) != 1:
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            k, = c.args
            v = self.machine.driver[k]
            self.ok(c, v)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/drive/set'
