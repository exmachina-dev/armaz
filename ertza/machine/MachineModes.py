# -*- coding: utf-8 -*-

import logging
from collections import namedtuple


class ContinueException(BaseException):
    pass


class AbstractMachineMode(object):
    _param = namedtuple('parameter', ['vtype', 'mode'])

    MachineMap = {
        'machine:operation_mode':   _param(str, 'rw'),
        'machine:serialnumber':     _param(str, 'r'),
        'machine:address':          _param(str, 'r'),
    }

    DirectAttributesGet = (
        'machine:serialnumber',
        'machine:operation_mode',
        'machine:infos',
        'machine:address',
    )

    DirectAttributesSet = (
    )

    def __init__(self, machine):
        self._machine = machine

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
        self._machine.setitem(key, self.MachineMap[key].vtype(value))

        if key in self.DirectAttributesSet:
            return self._machine.getitem(key)

        if key is 'machine:operation_mode':
            if isinstance(value, (list, tuple)):
                return self._machine.set_operation_mode(*value)
            else:
                return self._machine.set_operation_mode(value)

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
                    'machine:{}'.format(a): self._param(*p),
                })

        except AttributeError:
            pass

    def __setitem__(self, key, value):
        try:
            super().__setitem__(key, value)
        except ContinueException:
            try:
                skey = key.split(':', maxsplit=1)[1]
                self._machine.driver[skey] = value
            except KeyError as e:
                raise e

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except ContinueException:
            try:
                skey = key.split(':', maxsplit=1)[1]
                return self._machine.driver[skey]
            except KeyError as e:
                raise e


class MasterMachineMode(StandaloneMachineMode):
    _param = AbstractMachineMode._param

    AbstractMachineMode.MachineMap.update({
        'slaves':   _param(str, 'r'),
    })

    DefaultForwardKeys = {
        'machine:command:enable',
        'machine:command:cancel',
        'machine:command:clear_errors',
        'machine:command:reset',
    }

    ForwardKeys = {
        'torque': (
            'machine:torque_ref',
            'machine:torque_rise_time',
            'machine:torque_fall_time',
        ),
        'enhanced_torque': (
            'machine:torque_ref',
            'machine:torque_rise_time',
            'machine:torque_fall_time',
            'machine:velocity_ref',
        ),
        'speed': (
            'machine:velocity_ref',
            'machine:acceleration',
            'machine:deceleration',
        ),
        'position': (
            'machine:command:move_mode',
            'machine:command:go',
            'machine:command:set_home',
            'machine:command:go_home',
            'machine:velocity_ref',
            'machine:position_ref',
            'machine:acceleration',
            'machine:deceleration',
        ),
    }

    def __init__(self, machine):
        super().__init__(machine)

        self._slv_config = {}
        for s in self._machine.slaves:
            s_cf = s.slave.config
            self._slv_config[s.slave.serialnumber] = s_cf

    def __getitem__(self, key):
        g_list = []
        g_list.append(super().__getitem__(key))

        for s in self._machine.slaves:
            g_list.append(s.get_from_remote(key, block=True))

        return g_list

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

        for s in self._machine.slaves:
            sm = s.slave.slave_mode
            self._send_to_slave(s, sm, key, value)

    def _send_to_slave(self, slave, mode=None, key='', value=None):
        if not mode:
            return
        if key in self.ForwardKeys[mode].keys():
            value = self.get_value_for_slave(slave, key, value) or value
            slave.set_to_remote(key, value)
        if key in self.DefaultForwardKeys.keys():
            slave.set_to_remote(key, value)

    def get_value_for_slave(self, slave, key, value):
        if slave.slave.serialnumber not in self._slv_config.keys():
            logging.warn('No config registered for slave {!s}'.format(slave))
            return

        _cf = self._slv_config[slave.slave.serialnumber]
        vl_mode = _cf.get('{}_mode'.format(key), None)
        if vl_mode is None:
            return
        elif vl_mode not in ('forward', 'multiply', 'divide', 'add', 'substract', 'default',):
            logging.warn('Unrecognized mode {0} for {1}'.format(vl_mode, key))
            return

        vl_value = _cf.get('{}_value'.format(key), None)
        if vl_mode == 'foward':
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


class SlaveMachineMode(StandaloneMachineMode):
    _param = AbstractMachineMode._param

    AbstractMachineMode.MachineMap.update({
        'master':           _param(str, 'r'),
        'master_port':           _param(str, 'r'),
    })

    DirectAttributesGet = AbstractMachineMode.DirectAttributesGet + (
        'machine:master',
        'machine:master_port',
    )
