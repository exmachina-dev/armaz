# -*- coding: utf-8 -*-

from pymodbus.register_read_message import *
from pymodbus.register_write_message import *
from pymodbus.other_message import *
from pymodbus.mei_message import *
from pymodbus.pdu import *
import pymodbus.exceptions as pmde

import bitstring

from ...errors import ModbusMasterError


class MicroFlexE100Backend(object):
    reverse = False

    def __init__(self):
        pass

    def get_command(self, **kwargs):
        return self._get_multi_bools('command', **kwargs)

    def set_command(self, **kwargs):
        if 'target' not in kwargs:
            kwargs['target'] = 'all'
        if kwargs['target'] == 'all':
            target = self.devices
        else:
            target = (kwargs['target'],)

        rtn_data = list()
        for t in target:
            new_cmd = [False,]*32
            h = t.config.host
            for i, k in enumerate(self.command_keys):
                if k in kwargs.keys():
                    v = bool(kwargs[k])
                else:
                    try:
                        v = self.devices_state.command[h][k]
                    except KeyError:
                        v = None
                new_cmd[i] = (v)

            new_cmd = self._from_bools(new_cmd)
            kwargs['target'] = t
            rtn_data.append(self.write_comm(self.netdata['command'], new_cmd,
                **kwargs))
        return rtn_data

    def get_status(self, force=False, **kwargs):
        return self._get_multi_bools('status', **kwargs)

    def get_int(self, key, **kwargs):
        return self._get(key, self._to_int, **kwargs)

    def set_int(self, key, new_int, check=False, **kwargs):
        if check:
            return self._set(key, new_int, self._from_int, self._to_int,
                    **kwargs)
        return self._set(key, new_int, self._from_int, **kwargs)

    def get_float(self, key, **kwargs):
        return self._get(key, self._to_float, **kwargs)

    def set_float(self, key, new_float, check=False, **kwargs):
        if check:
            return self._set(key, new_float, self._from_float, self._to_float,
                    **kwargs)
        return self._set(key, new_float, self._from_float, **kwargs)

    def get_error_code(self, **kwargs):
        return self.get_int('error_code', **kwargs)

    def get_speed(self, **kwargs):
        return self.get_float('speed', **kwargs)

    def set_speed(self, new_speed, check=False, **kwargs):
        if self.reverse:
            new_speed *= -1
        return self.set_float('speed', new_speed, check, **kwargs)

    def get_direction(self, **kwargs):
        return self.reverse

    def set_direction(self, direction):
        self.reverse = bool(direction)
        return True

    def get_acceleration(self, **kwargs):
        return self.get_float('acceleration', **kwargs)

    def set_acceleration(self, new_acceleration, check=True, **kwargs):
        return self.set_float('acceleration', new_acceleration, **kwargs)

    def get_deceleration(self, **kwargs):
        return self.get_float('deceleration', **kwargs)

    def set_deceleration(self, new_deceleration, check=True, **kwargs):
        return self.set_float('deceleration', new_deceleration, **kwargs)

    def get_velocity(self, **kwargs):
        return self.get_float('velocity', **kwargs)

    def get_encoder_velocity(self, **kwargs):
        return self.get_float('encoder_velocity', **kwargs)

    def get_encoder_position(self, **kwargs):
        return self.get_int('encoder_position', **kwargs)

    def get_follow_error(self, **kwargs):
        return self.get_float('follow_error', **kwargs)

    def get_effort(self, **kwargs):
        return self.get_float('effort', **kwargs)

    def get_command_number(self, **kwargs):
        return self.get_int('command_number', **kwargs)

    def get_drive_temperature(self, **kwargs):
        return self.get_float('drive_temperature', **kwargs)

    def get_timeout(self, **kwargs):
        return self.get_int('timeout', **kwargs)

    def set_timeout(self, new_timeout, **kwargs):
        return self.set_int('timeout', new_timeout, **kwargs)

    def get_dropped_frames(self, **kwargs):
        return self.get_int('dropped_frames', **kwargs)

    def write_comm(self, comms, value, **kwargs):
        self._check_comms(comms)
        start = comms * self.nb_reg_by_comms

        return self.wmr(start, value, **kwargs)

    def read_comm(self, comms, force=False, **kwargs):
        self._check_comms(comms)
        start = comms * self.nb_reg_by_comms

        return self.rhr(start, self.nb_reg_by_comms, force, **kwargs)

    def check_connectivity(self, **kwargs):
        try:
            status = self.get_status(force=True, **kwargs)
            if type(status) == dict:
                return True
        except ModbusMasterError:
            pass
        return False

    def _get(self, key, format_function=None, **kwargs):
        if 'target' not in kwargs:
            kwargs['target'] = 'all'
        if kwargs['target'] == 'all':
            target = self.devices
        else:
            target = (kwargs['target'],)

        rtn_set = self._get_comms_set(self.read_comm, (self.netdata[key],), **kwargs)
        if rtn_set is -1:
            rtn = dict()
            for t in target:
                h = t.config.host
                rtn[h] = -1
            return rtn

        rtn_data = {}
        for i, rtn in enumerate(rtn_set):
            h = target[i].config.host
            if not rtn in (-1, None):
                if format_function:
                    rtn_data[h] = format_function(rtn[0]+rtn[1], key=key)
                else:
                    rtn_data[h] = rtn[0]+rtn[1]
            else:
                e = ModbusMasterError('Got None value for %s' % h, self.lg)
        return rtn_data

    def _get_multi_bools(self, key, **kwargs):
        return self._get(key, self._parse_bools, **kwargs)

    def _set(self, key, value, format_function, check=None, **kwargs):
        if 'target' not in kwargs:
            kwargs['target'] = 'all'

        rtn_set = self._set_comms_set(self.write_comm, (self.netdata[key],
            format_function(value),), **kwargs)
        if rtn_set is -1:
            return False

        return rtn_set

    def _check_comms(self, comms):
        if self.min_comms <= comms <= self.max_comms:
            return None

        raise ValueError('Comms number exceed limits.')

    @staticmethod
    def _get_comms_set(get_function, f_args=(), **kwargs):
        command_set = get_function(*f_args, **kwargs)
        if command_set is -1:
            return -1
        elif not type(command_set) is tuple:
            command_set = (command_set,)

        return command_set

    @staticmethod
    def _set_comms_set(set_function, f_args=(), **kwargs):
        command_set = set_function(*f_args, **kwargs)
        if command_set is -1:
            return -1
        elif not type(command_set) is tuple:
            command_set = (command_set,)

        return command_set

    def _parse_bools(self, data, key):
        command = self._to_bools(data)
        command.reverse()

        if key is 'command':
            keys = self.command_keys
        elif key is 'status':
            keys = self.status_keys

        dc = {}
        for k, v in zip(keys, command):
            dc[k] = bool(int(v))

        return dc

    @staticmethod
    def _to_int(bits, **kwargs):
        bits = bitstring.Bits(bin=bits)
        return bits.int

    @staticmethod
    def _from_int(int_value, **kwargs):
        bits = bitstring.Bits(int=int_value, length=32)
        return bits.unpack('uintbe:16, uintbe')

    @staticmethod
    def _to_float(bits, **kwargs):
        bits = bitstring.Bits(bin=bits)
        return bits.float

    @staticmethod
    def _from_float(float_value, **kwargs):
        bits = bitstring.Bits(float=float_value, length=32)
        return bits.unpack('uintbe:16, uintbe')

    @staticmethod
    def _to_bools(bits, **kwargs):
        bits = bitstring.Bits(bin=bits)
        l = list()
        for b in bits:
            l.append(b)

        return l

    @staticmethod
    def _from_bools(bools, **kwargs):
        bin_str = '0b'
        bools.reverse()
        for b in bools:
            if b is None:
                b = False
            bin_str += str(int(b))
        bits = bitstring.Bits(bin=bin_str)
        return bits.unpack('uintbe:16, uintbe')

    def _read_holding_registers(self, address, count, force=False, **kwargs):
        if 'target' in kwargs:
            target = kwargs['target']
        else:
            target = 'all'

        if target == 'all':
            rqs = list()
            for t in self.devices:
                rq = ReadHoldingRegistersRequest(
                        address, count, unit_id=t.config.node_id)
                rqs.append(self._rq(rq, force, target=t))
            return tuple(rqs)
        else:
            rq = ReadHoldingRegistersRequest(
                    address, count, unit_id=target.config.node_id)
            return self._rq(rq, force, target=target)

    def _read_input_registers(self, address, count, **kwargs):
        if 'target' in kwargs:
            target = kwargs['target']
        else:
            target = 'all'

        if target == 'all':
            rqs = list()
            for t in self.devices:
                rq = ReadInputRegistersRequest(
                        address, count, unit_id=t.config.node_id)
                rqs.append(self._rq(rq, target=t))
            return tuple(rqs)
        else:
            rq = ReadInputRegistersRequest(
                    address, count, unit_id=target.config.node_id)
            return self._rq(rq, target=target)

    def _write_single_register(self, address, value, **kwargs):
        if 'target' in kwargs:
            target = kwargs['target']
        else:
            target = 'all'

        if target == 'all':
            rqs = list()
            for t in self.devices:
                rq = WriteSingleRegisterRequest(
                        address, value, unit_id=t.config.node_id)
                rqs.append(self._rq(rq, target=t))
            return tuple(rqs)
        else:
            rq = WriteSingleRegisterRequest(
                    address, value, unit_id=target.config.node_id)
            return self._rq(rq, target=target)

    def _write_multiple_registers(self, address, value, **kwargs):
        if 'target' in kwargs:
            target = kwargs['target']
        else:
            target = 'all'

        if target == 'all':
            rqs = list()
            for t in self.devices:
                rq = WriteMultipleRegistersRequest(
                        address, value)
                rqs.append(self._rq(rq, target=t))
            return tuple(rqs)
        else:
            rq = WriteMultipleRegistersRequest(
                    address, value)
            return self._rq(rq, target=target)

    def _read_write_multiple_registers(self, address, value, **kwargs):
        if 'target' in kwargs:
            target = kwargs['target']
        else:
            target = 'all'

        if target == 'all':
            rqs = list()
            for t in self.devices:
                rq = ReadWriteMultipleRequest(
                        address, value, unit_id=t.config.node_id)
                rqs.append(self._rq(rq, target=t))
            return tuple(rqs)
        else:
            rq = ReadWriteMultipleRegistersRequest(
                    address, value, unit_id=target.config.node_id)
            return self._rq(rq, target=target)

    # Shortcuts
    rhr = _read_holding_registers
    rir = _read_input_registers
    wsr = _write_single_register
    wmr = _write_multiple_registers
    rwmr = _read_write_multiple_registers

    def _rq(self, rq, force=False, **kwargs):
        if 'target' in kwargs:
            target = kwargs['target']
        else:
            target = self.target

        try:
            if not force and not self.connected.is_set():
                return -1
            response = target.driver.end.execute(rq)
            rpt = type(response)
            if rpt == ExceptionResponse:
                raise ModbusMasterError('Exception received during execution.') from response
            elif rpt == WriteMultipleRegistersResponse:
                return True
            elif rpt == ReadHoldingRegistersResponse:
                regs = list()
                fmt = "{:0>"+str(self.word_lenght)+"b}"
                for i in range(self.nb_reg_by_comms):
                    regs.append(fmt.format(response.getRegister(i)))
                return regs
        except pmde.ConnectionException as e:
            self.connected.clear()
            raise ModbusMasterError('Unable to connect to slave', self.lg)
