# -*- coding: utf-8 -*-

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
            'encoder_velocity':     10,
            'encoder_position':     11,
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
            'driveEnable',
            'stop',
            'releaseBrake',
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


    def __init__(self, config, logger, restart_event, block_event):
        self.status = {}
        self.command = {}
        for k in self.command_keys:
            self.command[k] = False

        self.errorcode = None
        self.end = None
        self.connected = False
        self.config_request = None
        self.max_retry = 5
        self.retry = self.max_retry

        if config:
            self._config = config
            self.config_request = ConfigRequest(self._config)

        if logger:
            self.lg = logger
        else:
            import logging
            self.lg = logging.getLogger(__name__)

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
        if not self.connected:
            self.lg.debug("Initiated Modbus connection to %s:%s" % \
                    (self.device, self.port,))
            try:
                self.end = ModbusClient(host=self.device, port=self.port)
                self.end.connect()
                self.connected = True
                self.retry = self.max_retry
            except pmde.ConnectionException as e:
                self.lg.warn(repr(ModbusMasterError(
                        'Unable to connect to slave: %s' % e)))
            else:
                self.connected = False

    def close(self):
        self.end.close()
        self.connected = False

    def reconnect(self):
        if self.connected:
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
            self.nb_reg_by_comms = int(self.word_lenght / self.data_bit)
        except TypeError as e:
            raise ValueError('%s must be divided by %s' % (
                self.word_lenght, self.data_bit)) from e

    def get_command(self):
        command = self.read_comm(self.netdata['command'])

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

        if check:
            return self.get_command()
        return rtn

    def get_status(self):
        status = self.read_comm(self.netdata['status'])

        status = self._to_bools(status[0]+status[1])
        status.reverse()

        for k, v in zip(self.status_keys, status):
            self.status[k] = bool(int(v))

        return self.status

    def get_error_code(self):
        error = self.read_comm(self.netdata['error_code'])
        self.error_code = self._to_int(error[0]+error[1])

        return self.error_code

    def get_speed(self):
        speed = self.read_comm(self.netdata['speed'])
        self.speed = self._to_float(speed[0]+speed[1])

        return self.speed

    def set_speed(self, new_speed, check=True):
        new_speed = _from_float(new_speed)
        rtn = self.write_comm(self.netdata['speed'], new_speed)

        if check:
            return self.get_speed()
        return rtn

    def get_encoder_velocity(self):
        ev = self.read_comm(self.netdata['encoder_velocity'])
        self.encoder_velocity = self._to_float(ev[0]+ev[1])

        return self.encoder_velocity

    def get_encoder_position(self):
        ep = self.read_comm(self.netdata['encoder_position'])
        self.encoder_position = self._to_int(ep[0]+ep[1])

        return self.encoder_position

    def get_drive_temperature(self):
        temp = self.read_comm(self.netdata['drive_temperature'])
        self.drive_temperature = self._to_float(temp[0]+temp[1])

        return self.drive_temperature

    def get_dropped_frames(self):
        df = self.read_comm(self.netdata['dropped_frames'])
        self.dropped_frames = self._to_int(df[0]+df[1])

        return self.dropped_frames

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

    @retry(ModbusMasterError, tries=3, delay=1)
    def _rq(self, rq):
        try:
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
            raise ModbusMasterError('Unable to connect to slave')


if __name__ == "__main__":
    mb = ModbusBackend(None, None, None, None)

    mb.device = '192.168.100.2'
    mb.port = 502
    mb.node_id = 2
    mb.word_lenght = 16
    mb.data_bit = 8
    mb.nb_reg_by_comms = int(mb.word_lenght / mb.data_bit)
