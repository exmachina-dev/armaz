# -*- coding: utf-8 -*-

from pylibmodbus import ModbusRtu
Modbus = ModbusRtu

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
        self.end = Modbus(self.device, self.baudrate,
                self.parity, self.data_bit, self.stop_bit)
        self.end.rtu_set_serial_mode(Modbus.RTU_RS485)

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
        if self.min_comms <= comms <= self.max_comms:
            start = comms * self.nb_reg_by_comms
            return self.end.read_registers(start, self.nb_reg_by_comms)
        else:
            raise ValueError('Comms number exceed limits.')


if __name__ == "__main__":
    from ertza.utils import FakeConfig

    mb = ModbusBackend(FakeConfig(), None, None, None)
    print(mb.dump_config())
    mb.connect()
    mb.read_comm(1)
