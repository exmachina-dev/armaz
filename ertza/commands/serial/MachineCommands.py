# -*- coding: utf-8 -*-

from ertza.commands.SerialCommand import SerialCommand


class MachineSet(SerialCommand):

    def execute(self, c):
        if len(c.args) < 2:
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            k, v, = c.args
            self.machine[k] = v
            self.ok(c, k, v)
        except Exception as e:
            self.error(c, k, str(e))

    @property
    def alias(self):
        return 'machine.set'


class MachineGet(SerialCommand):

    def execute(self, c):
        if len(c.args) != 1:
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            k, = c.args
            v = self.machine[k]
            self.ok(c, k, v)
        except Exception as e:
            self.error(c, k, str(e))

    @property
    def alias(self):
        return 'machine.get'
