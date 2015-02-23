# -*- coding: utf-8 -*-

from pymodbus.client.sync import ModbusTcpClient as ModbusClient

from pymodbus.register_read_message import *
from pymodbus.register_write_message import *
from pymodbus.other_message import *
from pymodbus.mei_message import *
from pymodbus.pdu import *

import bitstring

from ertza.config import ConfigRequest
import ertza.errors as err


class ModbusBackend(object):
    def __init__(self, config, logger, restart_event, block_event):
        self.status = {}
        self.command = {}
        self.end = None

        self._config = config
        self.lg = logger
        self.config_request = ConfigRequest(self._config)

        self.available_functions = [
                3,     # Read holding registers
                4,     # Read input registers
                6,     # Write single register
                16,     # Write multiples registers
                23,     # Read/write multiple registers
                ]

        self.status_keys = (
                'drive_enable_ready',
                'drive_enable',
                'drive_enable_input',
                'motor_brake',
                )

        self.get_config()
        self.min_comms = 1
        self.max_comms = 99


    def connect(self):
        self.lg.debug("Initiated Modbus connection to %s:%s" % \
                (self.device, self.port,))
        self.end = ModbusClient(host=self.device, port=self.port)
        self.end.connect()

    def close(self):
        self.end.close()

    def reconnect(self):
        self.close()
        self.get_config()
        self.connect()

    def get_config(self):
        try:
            self.device = self.config_request.get(
                'modbus', 'device', '192.168.100.2')
            if self.device:
                self.device = str(self.device)
            else:
                raise ValueError('Network device must be a string.')
        except ValueError as e:
            raise err.ConfigError('Network device must be a string.') from e

        try:
            self.port = int(self.config_request.get(
                'modbus', 'port', 502))
        except ValueError as e:
            raise err.ConfigError('Port must be an int.') from e

        try:
            self.node_id = int(self.config_request.get(
                'modbus', 'node_id', 2))
        except ValueError as e:
            raise err.ConfigError('Node id must be an int.') from e

        try:
            self.word_lenght = int(self.config_request.get(
                'modbus', 'word_lenght', 16))
        except ValueError as e:
            raise err.ConfigError('Word lenght must be an int.') from e

        try:
            self.data_bit = int(self.config_request.get(
                'modbus', 'data_bit', 8))
        except ValueError as e:
            raise err.ConfigError('Data bit must be an int.') from e

        try:
            self.nb_reg_by_comms = int(self.word_lenght / self.data_bit)
        except TypeError as e:
            raise ValueError('%s must be divided by %s' % (
                self.word_lenght, self.data_bit)) from e

    def get_command(self):
        command = self.read_comm(0x01)

        keys = ('driveEnable', 'stop', 'releaseBrake',)

        command = self._to_bools(command[0]+command[1])
        command.reverse()

        for k, v in zip(keys, command):
            self.command[k] = bool(int(v))

        return self.command

    def get_status(self):
        status = self.read_comm(0x02)

        status = self._to_bools(status[0]+status[1])
        status.reverse()

        for k, v in zip(self.status_keys, status):
            self.status[k] = bool(int(v))

        return self.status

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

    def _to_bools(self, bits):
        bits = bitstring.Bits(bin=bits)
        l = list()
        for b in bits:
            l.append(b)

        return l

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


if __name__ == "__main__":
    from ertza.utils import FakeConfig

    mb = ModbusBackend(FakeConfig(), None, None, None)
    mb.device = '/dev/pts/1'
    mb.baudrate = 9600
    print(
'''
Use socat -d -d pty,raw,echo=0 pty,raw,echo=0 to create a fake serial line.
You can use cat < /dev/pts/11 to read output and echo 'something' > /dev/pts/11
to write in serial line.
'''
    )
    print(mb.dump_config())
    mb.connect()
    mb.read_comm(1)
