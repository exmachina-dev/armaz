# -*- coding: utf-8 -*-

from pymodbus.client.sync import ModbusSerialClient as ModbusClient

from pymodbus.register_read_message import *
from pymodbus.register_write_message import *
from pymodbus.other_message import *
from pymodbus.mei_message import *
from pymodbus.pdu import *

from ertza.config import ConfigRequest
import ertza.errors as err


class ModbusBackend(object):
    def __init__(self, config, logger, restart_event, block_event):
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

        self.get_config()
        self.min_comms = 1
        self.max_comms = 99


    def connect(self):
        self.end = ModbusClient(method='rtu', port=self.device,
                baudrate=self.baudrate, parity=self.parity,
                bytesize=self.data_bit, stopbits=self.stop_bit)

    def close(self):
        self.end.close()

    def reconnect(self):
        self.close()
        self.get_config()
        self.connect()

    def get_config(self):
        try:
            self.device = self.config_request.get(
                'modbus', 'device', '/dev/ttyS0')
            if self.device:
                self.device = str(self.device)
            else:
                raise ValueError('Serial device must be a string.')
        except ValueError as e:
            raise err.ConfigError('Serial device must be a string.') from e

        try:
            self.baudrate = int(self.config_request.get(
                'modbus', 'baudrate', 57600))
            if not self.baudrate in (4800, 9600, 19200, 38400, 57600, 115200):
                raise err.ConfigError('Incorrect baudrate: %s' % self.baurate)
        except ValueError as e:
            raise err.ConfigError('Baudrate must be an int.') from e

        try:
            self.parity = self.config_request.get(
                'modbus', 'parity', 'N')
            if not self.parity in ('N', 'E', 'O'):
                raise err.ConfigError('Incorrect parity: %s' % self.parity)
        except ValueError as e:
            raise err.ConfigError('Parity must be a string.') from e

        try:
            self.stop_bit = int(self.config_request.get(
                'modbus', 'stop_bit', 1))
        except ValueError as e:
            raise err.ConfigError('Stop bit must be an int.') from e

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


    def dump_config(self):
        cf = 'dev: %s, baud: %s, parity: %s, data_bit: %s, stop_bit: %s, \
world_lenght: %s, reg_by_comms: %s' % \
                (self.device, self.baudrate, self.parity,
                self.data_bit, self.stop_bit,
                self.word_lenght, self.nb_reg_by_comms)
        return cf

    def read_comm(self, comms):
        self._check_comms(comms)
        start = comms * self.nb_reg_by_comms

        return self.rhr(start, self.nb_reg_by_comms)

    def _check_comms(self, comms):
        if self.min_comms <= comms <= self.max_comms:
            return None

        raise ValueError('Comms number exceed limits.')

    def _read_holding_registers(self, address, count):
            rq = ReadHoldingRegistersRequest(
                    address, count, unit_id=self.node_id)
            return self._rq(rq)

    def _read_input_registers(self, address, count):
            rq = ReadInputRegistersRequest(
                    address, count, unit_id=self.node_id)

    def _write_single_register(self, address, value):
            rq = WriteSingleRegisterRequest(
                    address, value, unit_id=self.node_id)
            return self._rq(rq)

    def _write_multiple_registers(self, address, value):
            rq = WriteMultipleRegistersRequest(
                    address, value, unit_id=self.node_id)

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
        self.end.execute(rq)


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
