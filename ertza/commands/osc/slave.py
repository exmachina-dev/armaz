# -*- coding: utf-8 -*-

import logging

from ertza.commands import UnbufferedCommand
from ertza.commands import OscCommand

logging = logging.getLogger('ertza.commands.osc')


class SlaveCommand(OscCommand):
    """
    Ensure machine is in slave mode.
    """

    def check_slave_mode(self, c, reply=True):
        if self.machine.slave_mode:
            return True

        if reply:
            uuid, *args = c.args
            self.error(c, uuid, 'Slave mode not activated')
        return False

    def check_args(self, c, comp_op='eq', v=1, reply=True):
        comp = super().check_args(c, comp_op, v+1, reply=False)
        uuid, *args = c.args
        if not comp and reply:
            i = {
                'alias': self.alias,
                'len': len(c.args), 'op': comp_op, 'v': v,
                'args': ' '.join(map(str, args)),
            }
            self.error(c, uuid,  'Invalid number of arguments for {alias} '
                       '({len} {op} {v}: {args})'.format(**i))

        return comp


class SlaveGet(SlaveCommand, UnbufferedCommand):
    """
    Received by a slave.
    """

    def execute(self, c):
        uuid, *args = c.args
        if args[0] not in ('machine:operating_mode', 'machine:serialnumber') \
                and not self.check_slave_mode(c):
            return

        if not self.check_args(c, 'eq', 1):
            return

        try:
            dst = args[0]
            val = self.machine.get(dst, tick=True)
            self.ok(c, uuid, dst, val)
        except Exception as e:
            logging.error(repr(e))
            self.error(c, uuid, dst, repr(e))

    @property
    def alias(self):
        return '/slave/get'


class SlaveSet(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_args(c, 'ge', 2) or \
                not self.check_args(c, 'le', 3):
            return

        try:
            uuid, *args = c.args
            key, *values = args
            if key == 'machine:operating_mode':

                if len(values) == 1:
                    mode, master = values[0], None
                else:
                    mode, master = values
                self.machine.set_operating_mode(mode, master=master)
                self.ok(c, uuid, *args)
                return
            else:
                if not self.check_slave_mode(c):
                    return

            val = self.machine.set(key, *values, tick=True)

            if isinstance(val, (tuple, list)):
                self.ok(c, uuid, key, *val)
            else:
                self.ok(c, uuid, key, val)
        except Exception as e:
            logging.exception(e)
            args = values + [str(e),]
            self.error(c, uuid, key, *args)

    @property
    def alias(self):
        return '/slave/set'


class SlaveRegister(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_args(c, 'le', 1):
            return

        try:
            self.machine.set_operating_mode('slave')
            uuid = c.args[0]
            self.ok(c, uuid)
        except Exception as e:
            self.error(c, uuid, e)

    @property
    def alias(self):
        return '/slave/register'


class SlaveFree(SlaveCommand, UnbufferedCommand):

    def execute(self, c):
        if not self.check_slave_mode(c, reply=False):
            self.error(c, uuid, 'Cannot free slave: Slave mode not activated')

        try:
            self.machine.set_operating_mode()
            uuid = c.args[0]
            self.ok(c, uuid)
        except Exception as e:
            self.error(c, uuid, e)

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
        sl = self.machine.get_slave(address=c.sender.hostname)
        if not sl:
            raise ValueError('No slave returned')
        if sl.inlet is None:
            logging.error('Slave isn\'t started yet')
        else:
            sl.inlet.send(c)


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
