# -*- coding: utf-8 -*-

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
            for a, p in drv_attr_map.items():
                StandaloneMachineMode.MachineMap.update({
                    'machine:{}'.format(a): self._param(*p),})
                print(a, p)

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


class MasterMachineMode(AbstractMachineMode):
    _param = AbstractMachineMode._param

    AbstractMachineMode.MachineMap.update({
        'slaves':   _param(str, 'r'),
    })


class SlaveMachineMode(AbstractMachineMode):
    _param = AbstractMachineMode._param

    AbstractMachineMode.MachineMap.update({
        'master':           _param(str, 'r'),
        'master_port':           _param(str, 'r'),
    })

    DirectAttributesGet = AbstractMachineMode.DirectAttributesGet + (
        'machine:master',
        'machine:master_port',
    )
