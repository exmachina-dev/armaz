# -*- coding: utf-8 -*-

import pickle

from ertza.commands.AbstractCommands import UnbufferedCommand
from ertza.commands.OscCommand import OscCommand


class SlaveCommand(OscCommand):
    """
    Ensure machine is in slave mode.
    """

    def execute(self, c):
        if self.machine.slave_mode != 'slave':
            self.error(c, 'Slave mode not activated')
            return


class SlaveGet(SlaveCommand, UnbufferedCommand):
    """
    Received by a slave.
    """

    def execute(self, c):
        super().execute(c)

        if not self.check_args(c, 'eq', 1):
            return

        try:
            key = c.args
            self.ok(c, key, self.machine[key])
        except Exception as e:
            self.error(c, key, e)

    @property
    def alias(self):
        return '/slave/get'


class SlaveSet(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        super().execute(c)

        if not self.check_args(c, 'eq', 2):
            return

        try:
            key, value = c.args
            self.machine[key] = value
            self.ok(c, key, value)
        except Exception as e:
            self.error(c, key, value, e)

    @property
    def alias(self):
        return '/slave/set'


class SlaveFree(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        super().execute(c)

        try:
            self.machine.set_slave_mode()
            self.ok(c)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/slave/free'


class SlaveMode(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_args(c, 'eq', 1):
            return

        try:
            k, = c.args
            v = self.machine.driver[k]
            self.ok(c, k, v)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/machine/slave/mode'


class SlaveGetResponse(OscCommand, UnbufferedCommand):

    def execute(self, c):
        key, value, = c.args
        sl = self.machine.get_slave(address=c.sender.hostname)
        sl.inlet.send(pickle.pickle(c))

    @property
    def alias(self):
        return '/slave/get/ok'


class SlaveGetError(SlaveGetResponse):
    @property
    def alias(self):
        return '/slave/get/error'


class SlaveSetResponse(SlaveGetResponse, UnbufferedCommand):

    @property
    def alias(self):
        return '/slave/set/ok'


class SlaveSetError(SlaveSetResponse):
    @property
    def alias(self):
        return '/slave/set/error'
