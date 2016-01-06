# -*- coding: utf-8 -*-

import logging

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
            dst, = c.args
            to, key = dst.split(':')
            target = getattr(self, to)
            self.ok(c, dst, target[key])
        except Exception as e:
            self.error(c, dst, e)

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


class SlaveRegister(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        try:
            self.machine.set_slave_mode('slave')
            self.ok(c)
        except Exception as e:
            self.error(c, e)

    @property
    def alias(self):
        return '/slave/register'


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


class SlavePing(OscCommand, UnbufferedCommand):

    def execute(self, c):
        logging.info('Ping request from %s' % c.sender)
        self.ok(c)

    @property
    def alias(self):
        return '/slave/ping'


# -- Responses from slave --


class SlaveResponse(OscCommand, UnbufferedCommand):
    def execute(self, c):
        i, sl = self.machine.get_slave(address=c.sender.hostname)
        sl.inlet.put(c)
        logging.debug('Putting {0} in {1}'.format(
            str(c), sl.inlet.__class__.__name__))


class SlaveRegisterResponse(SlaveResponse):
    @property
    def alias(self):
        return '/slave/register/ok'


class SlaveGetResponse(SlaveResponse):
    @property
    def alias(self):
        return '/slave/get/ok'


class SlaveGetError(SlaveResponse):
    @property
    def alias(self):
        return '/slave/get/error'


class SlaveSetResponse(SlaveResponse):
    @property
    def alias(self):
        return '/slave/set/ok'


class SlaveSetError(SlaveResponse):
    @property
    def alias(self):
        return '/slave/set/error'


class SlavePingResponse(SlaveResponse):
    @property
    def alias(self):
        return '/slave/ping/ok'
