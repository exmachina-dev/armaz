# -*- coding: utf-8 -*-

import time
import logging
from collections import namedtuple

logging = logging.getLogger(__name__)


class ContinueException(BaseException):
    pass


class AbstractMachineMode(object):
    _param = namedtuple('parameter', ['vtype', 'mode'])

    MachineMap = {
        'operation_mode':   _param(str, 'rw'),
        'serialnumber':     _param(str, 'r'),
        'address':          _param(str, 'r'),
    }

    DirectAttributesGet = (
        'serialnumber',
        'operation_mode',
        'infos',
        'address',
    )

    DirectAttributesSet = (
    )

    StaticKeys = (
        'machine:acceleration',
        'machine:decceleration',
        'machine:torque_rise_time',
        'machine:torque_fall_time',
    )

    def __init__(self, machine):
        self._machine = machine
        self._last_values = {}

    def _check_read_access(self, key):
        self._check_key(key)
        if 'r' not in self.MachineMap[key].mode:
            raise KeyError('{} is not readable'.format(key))

    def _check_write_access(self, key):
        self._check_key(key)
        if 'w' not in self.MachineMap[key].mode:
            raise KeyError('{} is not writable'.format(key))

    def _check_key(self, key):
        if key not in self.MachineMap.keys():
            raise KeyError('{0} not in {1.__class__.__name__} keys'.format(key, self))

    def __getitem__(self, key):
        self._check_read_access(key)

        if key in self.DirectAttributesGet:
            return self._machine.getitem(key)

        raise ContinueException()

    def __setitem__(self, key, value):
        self._check_write_access(key)

        if key == 'operation_mode':
            if isinstance(value, (list, tuple)):
                return self._machine.set_operation_mode(*value)
            else:
                return self._machine.set_operation_mode(value)

        if key in self.DirectAttributesSet:
            return self._machine.setitem(key)

        raise ContinueException()


class StandaloneMachineMode(AbstractMachineMode):
    _param = AbstractMachineMode._param

    def __init__(self, machine):
        super().__init__(machine)

        try:
            drv_attr_map = self._machine.driver.get_attribute_map()
            logging.info('Appending driver attribute map '
                         'to {0.__class__.__name__}'.format(self))
            for a, p in drv_attr_map.items():
                StandaloneMachineMode.MachineMap.update({
                    '{}'.format(a): self._param(*p),
                })

        except AttributeError:
            pass

    def __getitem__(self, key):
        try:
            res = super().__getitem__(key)
        except ContinueException:
            res = self._machine.driver[key]

        return res

    def __setitem__(self, key, value):
        try:
            super().__setitem__(key, value)
        except ContinueException:
            self._machine.driver[key] = value

        if key in self.StaticKeys:
            self.StaticKeys[key] = value


class MasterMachineMode(StandaloneMachineMode):
    _param = AbstractMachineMode._param

    AbstractMachineMode.MachineMap.update({
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
        'speed': (
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

        self.guard_interval = 0.25

        self._slv_config = {}
        for s in self._machine.slaves:
            s_cf = s.slave.config
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

        if not value:
            if key in self.StaticKeys:
                value = self._last_values.get(key, self._machine[key])
            else:
                try:
                    value = self.get_guarded_value(key)
                except ContinueException:
                    logging.warn('No value returned for {}'.format(key))
                    return

        vl_value = _cf.get('{}_value'.format(key), None)
        if vl_mode == 'forward':
            return value
        elif vl_mode == 'multiply':
            return vl_value * value
        elif vl_mode == 'divide':
            return vl_value / value
        elif vl_mode == 'add':
            return vl_value + value
        elif vl_mode == 'substract':
            return vl_value - value
        elif vl_mode == 'default':
            return vl_value

    def get_guarded_value(self, key):
        gvalue, gtime = self.ValueGuard.get(key, (None, None,))
        if gvalue is not None:
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


class SlaveMachineMode(StandaloneMachineMode):
    _param = AbstractMachineMode._param

    AbstractMachineMode.MachineMap.update({
        'master':           _param(str, 'r'),
        'master_port':           _param(str, 'r'),
    })

    DirectAttributesGet = AbstractMachineMode.DirectAttributesGet + (
        'master',
        'master_port',
    )
