# -*- coding: utf-8 -*-

import struct

from ertza.commands import SerialCommand


class MachineSet(SerialCommand):
    _uint_keys = (
        'machine:command:control_mode',
        'machine:command:move_mode',
    )
    _float_keys = (
        'machine:torque_ref',
        'machine:velocity_ref',
        'machine:position_ref',
        'machine:acceleration',
        'machine:deceleration',
    )
    _bool_keys = (
        'machine:command:enable',
        'machine:command:cancel',
        'machine:command:reset',
        'machine:command:go',
        'machine:command:go_home',
        'machine:command:set_home',
        'machine:command:stop',
    )

    def execute(self, c):
        if len(c.args) < 2:
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            k, v, = c.args
            nk = k.decode().replace('.', ':')
            vt = None
            if nk in self._float_keys:
                v = struct.unpack('f', v)[0]
                vt = float
            elif nk in self._uint_keys:
                v = struct.unpack('I', v)[0]
                vt = int
            elif nk in self._bool_keys:
                v = struct.unpack('?', v)[0]
                vt = bool

            self.machine[nk] = v
            nk = nk.split(':', maxsplit=1)[1] if nk.startswith('machine:') else nk
            nv = self.machine.driver.frontend.input_value(
                nk, self.machine.driver.frontend.output_value(nk, v))
            if vt is not None:
                self.ok(c, k, vt(nv))
            else:
                self.ok(c, k, nv)
        except Exception as e:
            self.error(c, k, str(e))

    @property
    def alias(self):
        return 'machine.set'


class MachineGet(SerialCommand):

    def execute(self, c):
        if not self.check_args(c, 'eq', 1):
            return

        try:
            k, = c.args
            nk = k.decode().replace('.', ':')
            v = self.machine[nk]
            if v is not None:
                self.ok(c, k, v)
            else:
                raise ValueError('Bad machine response: None')
        except Exception as e:
            self.error(c, k, str(e))

    @property
    def alias(self):
        return 'machine.get'
