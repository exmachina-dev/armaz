# -*- coding: utf-8 -*-

import logging

from ertza.commands import UnbufferedCommand
from ertza.commands import OscCommand

logging = logging.getLogger('ertza.commands.osc')


class SlaveCommand(OscCommand):
    """
    Ensure machine is in slave mode.
    """

    def execute(self, c):
        if not self.machine.slave_mode:
            uid, *args = c.args
            self.error(c, uid, 'Slave mode not activated')
            return True


class SlaveGet(SlaveCommand, UnbufferedCommand):
    """
    Received by a slave.
    """

    def execute(self, c):
        if c.args[1] not in ('machine:operation_mode', 'machine:serialnumber'):
            if super().execute(c):
                return

        if not self.check_args(c, 'eq', 2):
            return

        try:
            uid, dst = c.args
            self.ok(c, uid, dst, self.machine[dst])
        except Exception as e:
            logging.error(repr(e))
            self.error(c, uid, dst, repr(e))

    @property
    def alias(self):
        return '/slave/get'


class SlaveSet(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_args(c, 'ge', 3):
            return

        try:
            if c.args[1] is 'machine:operation_mode':
                self.machine.set_operating_mode(*c.args[2:])
                self.ok(c, uid, dst, *args)
                return
            else:
                if super().execute(c):
                    return

            uid, dst, *args = c.args

            if len(args) == 1:
                self.machine[dst] = args[0]
            else:
                self.machine[dst] = args

            self.ok(c, uid, dst, *args)
        except Exception as e:
            logging.error(repr(e))
            self.error(c, uid, dst, *(list(args) + [repr(e),]))

    @property
    def alias(self):
        return '/slave/set'


class SlaveRegister(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_args(c, 'le', 2):
            return

        try:
            self.machine.set_operating_mode('slave')
            uid = c.args[0]
            self.ok(c, uid)
        except Exception as e:
            self.error(c, uid, e)

    @property
    def alias(self):
        return '/slave/register'


class SlaveFree(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        super().execute(c)

        try:
            self.machine.set_operating_mode()
            uid = c.args[0]
            self.ok(c, uid)
        except Exception as e:
            self.error(c, uid, e)

    @property
    def alias(self):
        return '/slave/free'


class SlavePing(OscCommand, UnbufferedCommand):

    def execute(self, c):
        logging.info('Ping request from %s' % c.sender)

        if len(c.args) == 1:
            self.ok(c, *c.args)
        else:
            self.ok(c)

    @property
    def alias(self):
        return '/slave/ping'


# -- Responses from slave --


class SlaveResponse(OscCommand, UnbufferedCommand):
    def execute(self, c):
        i, sl = self.machine.get_slave(address=c.sender.hostname)
        if not sl:
            raise ValueError('No slave returned')
        sl.inlet.put(c)


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
