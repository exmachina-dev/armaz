# -*- coding: utf-8 -*-

import time
import logging

from .abstract_machinemode import ContinueException, MachineModeException
from .standalone import StandaloneMachineMode

logging = logging.getLogger('ertza.machine.modes.master')


class MasterMachineMode(StandaloneMachineMode):
    _param = StandaloneMachineMode._param

    StandaloneMachineMode.MachineMap.update({
        'slaves':   _param(str, 'r'),
    })

    DefaultForwardKeys = (
        'command:enable',
        'command:cancel',
        'command:clear_errors',
        'command:reset',
    )

    ForwardKeys = {
        'torque': (
            'torque_ref',
            'torque_rise_time',
            'torque_fall_time',
        ),
        'enhanced_torque': (
            'torque_ref',
            'torque_rise_time',
            'torque_fall_time',
            'velocity_ref',
        ),
        'velocity': (
            'velocity_ref',
            'acceleration',
            'deceleration',
        ),
        'position': (
            'command:move_mode',
            'command:go',
            'command:set_home',
            'command:go_home',
            'velocity_ref',
            'position_ref',
            'acceleration',
            'deceleration',
        ),
    }

    ValueGuard = {}

    def __init__(self, machine):
        super().__init__(machine)

        self.guard_interval = 0.03

        self._slv_config = {}
        for s in self._machine.slaves:
            s_cf = {}
            for k, v in s.slave.config.items():
                if k.endswith('_mode'):
                    s_cf[k.replace('.', ':')] = v
                else:
                    s_cf[k.replace('.', ':')] = float(v)
            self._slv_config[s.slave.serialnumber] = s_cf

    def _send_to_slave(self, slave, mode=None, key='', value=None):
        if not mode:
            return
        if key in self.ForwardKeys[mode]:
            value = self.get_value_for_slave(slave, key, value) or value
            slave.set_to_remote(key, value)
        if key in self.DefaultForwardKeys:
            slave.set_to_remote(key, value)

    def get_value_for_slave(self, slave, key, value=None):
        if slave.slave.serialnumber not in self._slv_config.keys():
            logging.warn('No config registered for slave {!s}'.format(slave))
            return

        _cf = self._slv_config[slave.slave.serialnumber]
        vl_mode = _cf.get('{}_mode'.format(key), 'forward')

        if vl_mode not in ('forward', 'multiply', 'divide', 'add', 'substract', 'default',):
            logging.warn('Unrecognized mode {0} for {1}'.format(vl_mode, key))
            return

        vl_value = _cf.get('{}_value'.format(key), None)
        if vl_mode in ('multiply', 'divide', 'add', 'substract', 'default',) and vl_value is None:
            raise MachineModeException('No value configured for '
                                       '{0} in {1!s}'.format(key, slave))
        if vl_mode == 'default':
            return vl_value

        if not value:
            if key in self.StaticKeys:
                value = self._last_values.get(key, self._machine[key])
            else:
                try:
                    value = self.get_guarded_value(key)
                except ContinueException:
                    raise MachineModeException('No value returned for '
                                               '{0.slave.serialnumber} '
                                               '({1} asked)'.format(slave, key))

        if vl_mode == 'forward':
            return value
        elif vl_mode == 'multiply':
            return vl_value * value
        elif vl_mode == 'divide':
            return vl_value / value
        elif vl_mode == 'add':
            logging.debug('added {} to {}'.format(vl_value, value))
            if value >= 0:
                return vl_value + value
            else:
                return vl_value - value
        elif vl_mode == 'substract':
            if value >= 0:
                return vl_value - value
            else:
                return vl_value + value

    def get_guarded_value(self, key):
        gvalue, gtime = self.ValueGuard.get(key, (None, None,))
        if gtime is not None:
            if time.time() - gtime > self.guard_interval:
                nvalue = self._machine[key]
                ntime = time.time()
                self.ValueGuard[key] = (nvalue, ntime)
                return nvalue
            else:
                return gvalue
        else:
            nvalue = self._machine[key]
            ntime = time.time()
            self.ValueGuard[key] = (nvalue, ntime)
            return nvalue
