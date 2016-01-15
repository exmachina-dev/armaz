# -*- coding: utf-8 -*-

from collections import namedtuple


class AbstractMachineMode(object):
    _param = namedtuple('parameter', ['vtype', 'mode'])

    MachineMap = {
        'operation_mode':   _param(str, 'r'),
        'serialnumber':     _param(str, 'r'),
        'address':          _param(str, 'r'),
    }

    def __init__(self, machine):
        self._machine = machine

    @classmethod
    def _check_read_access(key):
        StandaloneMachineMode._check_access(key)
        if 'r' not in StandaloneMachineMode.MachineMap[key].mode:
            raise KeyError('{} is not readable'.format(key))

    @classmethod
    def _check_write_access(key):
        StandaloneMachineMode._check_access(key)
        if 'w' not in StandaloneMachineMode.MachineMap[key].mode:
            raise KeyError('{} is not writable'.format(key))

    @classmethod
    def _check_key(key):
        if key not in StandaloneMachineMode.MachineMap.keys():
            raise KeyError('{} not in StandaloneMachineMode keys'.format(key))

    def __getitem__(self, key):
        key = key.split(':', maxsplit=1)[1] if key.startswith('machine:') else key
        self._check_read_access(key)
        return self._machine.getitem(key)

    def __setitem__(self, key, value):
        self._check_write_access(key)
        self._machine.setitem(key, self.MachineMap[key].vtype(value))


class StandaloneMachineMode(AbstractMachineMode):
    pass


class MasterMachineMode(AbstractMachineMode):
    _param = AbstractMachineMode._param

    AbstractMachineMode.MachineMap.update({
        'slaves':   _param(str, 'r'),
    })


class SlaveMachineMode(AbstractMachineMode):
    _param = AbstractMachineMode._param

    AbstractMachineMode.MachineMap.update({
        'master':           _param(str, 'r'),
    })
