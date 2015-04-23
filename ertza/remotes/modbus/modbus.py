# -*- coding: utf-8 -*-

from time import sleep

from multiprocessing import Process, Event

from pymodbus.client.sync import ModbusTcpClient as ModbusClient

from pymodbus.register_read_message import *
from pymodbus.register_write_message import *
from pymodbus.other_message import *
from pymodbus.mei_message import *
from pymodbus.pdu import *
import pymodbus.exceptions as pmde

import bitstring

from ...config import ConfigRequest
from ...errors import ConfigError, ModbusMasterError
from ...utils import retry


class ModbusBackend(object):
    netdata = {
            'command':              1,
            'status':               2,
            'error_code':           3,
            'speed':                4,
            'acceleration':         5,
            'deceleration':         6,
            'velocity':             7,
            'encoder_velocity':     10,
            'encoder_position':     11,
            'follow_error':         12,
            'effort':               13,
            'command_number':       20,
            'drive_temperature':    21,
            'dropped_frames':       50,
            }

    status_keys = (
            'drive_enable_ready',
            'drive_enable',
            'drive_enable_input',
            'motor_brake',
            'command_timeout',
            )

    command_keys = (
            'drive_enable',
            'drive_cancel',
            'clear_errors',
            )

    states = {
            'ready': (
                True,
                None,
                True,
                None,
                False,),
            'enabled': (
                True,
                True,
                True,
                False,
                False,),
            }

    watcher_interval = 0.001


    def __init__(self, config, logger, restart_event, block_event=None):
        self.status = {}
        self.command = {}
        for k in self.command_keys:
            self.command[k] = False

        self.errorcode = None
        self.end = None
        self.connected = Event()
        self.watch = Event()
        self.watcher = None
        self.config_request = None
        self.max_retry = 5
        self.retry = self.max_retry
        self.restart_delay = 10
        self.restart_backoff = 2

        if config:
            self._config = config
            self.config_request = ConfigRequest(self._config)

        if logger:
            self.lg = logger
        else:
            import logging
            self.lg = logging.getLogger(__name__)

        if block_event:
            self.block_event = block_event

        self.available_functions = [
                3,     # Read holding registers
                4,     # Read input registers
                6,     # Write single register
                16,     # Write multiples registers
                23,     # Read/write multiple registers
                ]

        if self.config_request:
            self.load_config()

        self.min_comms = 1
        self.max_comms = 99


    @retry(ModbusMasterError, tries=3, delay=1)
    def connect(self):
        if not self.connected.is_set():
            self.lg.debug("Initiated Modbus connection to %s:%s" % \
                    (self.device, self.port,))
            try:
                self.end = ModbusClient(host=self.device, port=self.port)
                self.end.connect()
                if self.get_status():
                    self.connected.set()
                    self.retry = self.max_retry
                elif self.retry > 0:
                    self.lg.warn('Init failed, restarting in %s second' %
                            self.restart_delay)
                    self.retry -= 1
                    self.connected.wait(self.restart_delay)
                    self.restart_delay *= self.restart_backoff
                    self.connect()
                    return False

                self.lg.debug('Starting modbus watcher.')
                if self.watcher:
                    self.lg.debug('Waiting for existing watcher to exit.')
                    self.watch.set()
                    self.watcher.join()
                self.watcher = Process(target=self._state_watcher, args=(self,))
                self.watcher.daemon = True
                self.watch.clear()
                self.watcher.start()
            except pmde.ConnectionException as e:
                self.lg.warn(repr(ModbusMasterError(
                        'Unable to connect to slave: %s' % e)))
            else:
                self.connected.clear()

    def close(self):
        self.end.close()
        self.connected.clear()

    def reconnect(self):
        if self.connected.is_set():
            self.close()
        self.get_config()
        self.connect()

    def load_config(self):
        try:
            self.device = self.config_request.get(
                'modbus', 'device', '192.168.100.2')
            if self.device:
                self.device = str(self.device)
            else:
                raise ValueError('Network device must be a string.')
        except ValueError as e:
            raise ConfigError('Network device must be a string.') from e

        try:
            self.port = int(self.config_request.get(
                'modbus', 'port', 502))
        except ValueError as e:
            raise ConfigError('Port must be an int.') from e

        try:
            self.node_id = int(self.config_request.get(
                'modbus', 'node_id', 2))
        except ValueError as e:
            raise ConfigError('Node id must be an int.') from e

        try:
            self.word_lenght = int(self.config_request.get(
                'modbus', 'word_lenght', 16))
        except ValueError as e:
            raise ConfigError('Word lenght must be an int.') from e

        try:
            self.data_bit = int(self.config_request.get(
                'modbus', 'data_bit', 8))
        except ValueError as e:
            raise ConfigError('Data bit must be an int.') from e

        try:
            self.encoder_ratio = int(self.config_request.get(
                'modbus', 'encoder_ratio', 1000))
        except ValueError as e:
            raise ConfigError('Encoder ratio must be an int.') from e

        try:
            self.nb_reg_by_comms = int(self.word_lenght / self.data_bit)
        except TypeError as e:
            raise ValueError('%s must be divided by %s' % (
                self.word_lenght, self.data_bit)) from e

    def _state_watcher(self, master):
        while not master.watch.is_set():
            try:
                if master.connected.is_set():
                    master.get_command()
                    master.get_status()
                    master.get_speed()
                    master.get_velocity()
                    master.get_encoder_position()
                    master.get_effort()
                    master.get_drive_temperature()
                    try:
                        master.block_event.clear()
                    except AttributeError:
                        pass
                else:
                    try:
                        master.block_event.set()
                    except AttributeError:
                        pass
            except ModbusMasterError as e:
                master.lg.warn('State watcher got %s' % repr(e))

            master.watch.wait(ModbusBackend.watcher_interval)

    def get_command(self):
        command = self.read_comm(self.netdata['command'])
        if command is -1:
            return None

        command = self._to_bools(command[0]+command[1])
        command.reverse()

        for k, v in zip(self.command_keys, command):
            self.command[k] = bool(int(v))

        return self.command

    def set_command(self, check=True, **kwargs):
        new_cmd = [False,]*32
        for i, k in enumerate(self.command_keys):
            if k in kwargs.keys():
                v = bool(kwargs[k])
            else:
                v = self.command[k]
            new_cmd[i] = (v)

        new_cmd = self._from_bools(new_cmd)
        rtn = self.write_comm(self.netdata['command'], new_cmd)
        if rtn is -1:
            return None

        if check:
            return self.get_command()
        return rtn

    def get_status(self):
        status = self.read_comm(self.netdata['status'])
        if status is -1:
            return None

        status = self._to_bools(status[0]+status[1])
        status.reverse()

        for k, v in zip(self.status_keys, status):
            self.status[k] = bool(int(v))

        return self.status

    def get_error_code(self):
        error = self.read_comm(self.netdata['error_code'])
        self.error_code = self._to_int(error[0]+error[1])

        return self.error_code

    def _get(self, key, format_function=None):
        rtn = self.read_comm(self.netdata[key])
        if rtn is -1:
            return None

        if format_function:
            return format_function(rtn[0]+rtn[1])
        return rtn[0]+rtn[1]

    def _set(self, key, value, format_function, check=None):
        rtn = self.write_comm(self.netdata[key], format_function(value))
        if rtn is -1:
            return None

        if check:
            return self._get(key, check)
        return rtn

    def get_int(self, key):
        return self._get(key, self._to_int)

    def set_int(self, key, new_int, check=False):
        if check:
            return self._set(key, new_int, self._from_int, self._to_int)
        return self._set(key, new_int, self._from_int)

    def get_float(self, key):
        return self._get(key, self._to_float)

    def set_float(self, key, new_float, check=False):
        if check:
            return self._set(key, new_float, self._from_float, self._to_float)
        return self._set(key, new_float, self._from_float)

    def get_speed(self):
        return self.get_float('speed')

    def set_speed(self, new_speed, check=False):
        return self.set_float('speed', new_speed, check)

    def get_acceleration(self):
        return self.get_float('acceleration')

    def set_acceleration(self, new_acceleration, check=True):
        return self.set_float('acceleration', new_acceleration)

    def get_deceleration(self):
        return self.get_float('deceleration')

    def set_deceleration(self, new_deceleration, check=True):
        return self.set_float('deceleration', new_deceleration)

    def get_velocity(self):
        return self.get_float('velocity')

    def get_encoder_velocity(self):
        return self.get_float('encoder_velocity') / self.encoder_ratio

    def get_encoder_position(self):
        return self.get_int('encoder_position')

    def get_follow_error(self):
        return self.get_float('follow_error')

    def get_effort(self):
        return self.get_float('effort')

    def get_drive_temperature(self):
        return self.get_float('drive_temperature')

    def get_dropped_frames(self):
        return self.get_int('dropped_frames')

    def dump_config(self):
        cf = 'dev: %s, port: %s, data_bit: %s, \
world_lenght: %s, reg_by_comms: %s' % \
                (self.device, self.port, self.data_bit,
                self.word_lenght, self.nb_reg_by_comms)
        return cf

    def write_comm(self, comms, value):
        self._check_comms(comms)
        start = comms * self.nb_reg_by_comms

        return self.wmr(start, value)

    def read_comm(self, comms):
        self._check_comms(comms)
        start = comms * self.nb_reg_by_comms

        return self.rhr(start, self.nb_reg_by_comms)

    def _check_comms(self, comms):
        if self.min_comms <= comms <= self.max_comms:
            return None

        raise ValueError('Comms number exceed limits.')

    @staticmethod
    def _to_int(bits):
        bits = bitstring.Bits(bin=bits)
        return bits.int

    @staticmethod
    def _from_int(int_value):
        bits = bitstring.Bits(int=int_value, length=32)
        return bits.unpack('uintbe:16, uintbe')

    @staticmethod
    def _to_float(bits):
        bits = bitstring.Bits(bin=bits)
        return bits.float

    @staticmethod
    def _from_float(float_value):
        bits = bitstring.Bits(float=float_value, length=32)
        return bits.unpack('uintbe:16, uintbe')

    @staticmethod
    def _to_bools(bits):
        bits = bitstring.Bits(bin=bits)
        l = list()
        for b in bits:
            l.append(b)

        return l

    @staticmethod
    def _from_bools(bools):
        bin_str = '0b'
        bools.reverse()
        for b in bools:
            bin_str += str(int(b))
        bits = bitstring.Bits(bin=bin_str)
        return bits.unpack('uintbe:16, uintbe')

    def _read_holding_registers(self, address, count):
            rq = ReadHoldingRegistersRequest(
                    address, count, unit_id=self.node_id)
            return self._rq(rq)

    def _read_input_registers(self, address, count):
            rq = ReadInputRegistersRequest(
                    address, count, unit_id=self.node_id)
            return self._rq(rq)

    def _write_single_register(self, address, value):
            rq = WriteSingleRegisterRequest(
                    address, value, unit_id=self.node_id)
            return self._rq(rq)

    def _write_multiple_registers(self, address, value):
            rq = WriteMultipleRegistersRequest(
                    address, value, unit_id=self.node_id)
            return self._rq(rq)

    def _read_write_multiple_registers(self, address, value):
            rq = ReadWriteMultipleRegistersRequest(
                    address, value, unit_id=self.node_id)
            return self._rq(rq)

    # Shortcuts
    rhr = _read_holding_registers
    rir = _read_input_registers
    wsr = _write_single_register
    wmr = _write_multiple_registers
    rwmr = _read_write_multiple_registers

    def _rq(self, rq):
        try:
            if not self.connected.is_set():
                return -1
            response = self.end.execute(rq)
            rpt = type(response)
            if rpt == ExceptionResponse:
                return repr(response)
            elif rpt == WriteMultipleRegistersResponse:
                return repr(response)
            elif rpt == ReadHoldingRegistersResponse:
                regs = list()
                fmt = "{:0>"+str(self.word_lenght)+"b}"
                for i in range(self.nb_reg_by_comms):
                    regs.append(fmt.format(response.getRegister(i)))
                return regs
        except pmde.ConnectionException as e:
            self.connected.clear()
            raise ModbusMasterError('Unable to connect to slave')


if __name__ == "__main__":
    mb = ModbusBackend(None, None, None, None)

    mb.device = '192.168.100.2'
    mb.port = 502
    mb.node_id = 2
    mb.word_lenght = 16
    mb.data_bit = 8
    mb.encoder_ratio = 1000
    mb.nb_reg_by_comms = int(mb.word_lenght / mb.data_bit)
