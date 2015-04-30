# -*- coding: utf-8 -*-

from time import sleep
from collections import namedtuple

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
    modbusDevice = namedtuple('ModbusDevice', ['config', 'driver', 'watcher'])
    modbusDeviceConfig = namedtuple('ModbusDeviceConfig', ['host', 'port',
    'node_id', 'motor_config'])
    modbusDeviceDriver = namedtuple('ModbusDeviceDriver', ['config',
        'connected_event', 'error_event', 'drive_enable_event', 'end'])
    modbusDeviceWatcher = namedtuple('ModbusDeviceWatcher', ['config',
    'watch_event', 'process'])

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

    watcher_interval = 0.01


    def __init__(self, config, logger, restart_event, block_event=None,
            **kwargs):
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
        self.restart_init_delay = 10
        self.restart_delay = 10
        self.restart_backoff = 2

        self.devices = list()
        self.devices_config = list()

        self.kwargs = kwargs

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
            self.lg.debug("Initiated Modbus connection.")
            try:
                self.create_devices()
                for d in self.devices:
                    if d.driver.end.connect():
                        d.driver.connected_event.set()
                    d.driver.connected_event.wait(0.1)

                self.lg.debug('Starting modbus watchers.')
                for d in self.devices:
                    if d.watcher.process.is_alive() and not d.watcher.watch_event.is_set():
                        self.lg.debug('Waiting for existing watcher to exit.')
                        d.watcher.watch_event.set()
                        d.watcher.process.join()

                    d.watcher.process.daemon = True
                    d.watcher.watch_event.clear()
                    d.watcher.process.start()

                self.connected.set()
                for d in self.devices:
                    if not d.driver.connected_event.is_set():
                        self.connected.clear()
                        self.lg.error('%s not connected.' % d.config.host)

                if not self.connected.is_set() and self.retry < 0:
                    self.lg.warn('Init failed, restarting in %s second' %
                            self.restart_delay)
                    self.retry -= 1
                    self.connected.wait(self.restart_delay)
                    self.restart_delay *= self.restart_backoff
                    self.connect()
                    return False

                self.retry = self.max_retry
                self.restart_delay = self.restart_init_delay
                return True
            except pmde.ConnectionException as e:
                self.lg.warn(repr(ModbusMasterError(
                        'Unable to connect to slave: %s' % e)))

            self.connected.clear()

    def close(self):
        for d in self.devices:
            d.driver.set_speed(0)
            d.driver.set_command(drive_enable=0)
            d.watcher.watch_event.set()
            d.driver.end.close()

        self.connected.clear()

    def reconnect(self):
        if self.connected.is_set():
            self.close()
        self.get_config()
        self.connect()

    def create_devices(self):
        for _c in self.devices_config:
            self.lg.debug('Creating %s:%s:%s device.' % (_c.host, _c.port,
                _c.node_id))
            _driver = ModbusClient(host=_c.host, port=_c.port)
            _d = ModbusBackend.modbusDeviceDriver(_c,
                connected_event=Event(), error_event=Event(),
                drive_enable_event=Event(), end=_driver)

            _watcher = Process(target=self._state_watcher,
                    name='ertza.mw%s' % _c.node_id, args=(self, _c, _d,))
            _w = ModbusBackend.modbusDeviceWatcher(_c, watch_event=Event(),
                    process=_watcher)

            self.devices.append(ModbusBackend.modbusDevice( _c, _d, _w))

    def load_config(self):

        # Backend config
        try:
            self.auto_enable = bool(self.config_request.get(
                'modbus', 'auto_enable', False))
        except ValueError as e:
            raise ConfigError('Auto enable must be a bool.') from e

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

        # Default device config
        self.devices_config.append(self.load_device_config())

        if 'slave' in self.kwargs:
            _device = self.load_device_config(section='slave %s' %
                    self.kwargs['slave'])
            self.lg.info('Slave provided, adding %s to controlled devices.' %
                    _device[0])
            self.devices_config.append(_device)

    def load_device_config(self, section='modbus'):
        section = section

        try:
            _device = str(self.config_request.get(
                section, 'device', False))
        except ValueError as e:
            raise ConfigError('Network device must be a string.') from e

        try:
            _port = int(self.config_request.get(
                section, 'port', 502))
        except ValueError as e:
            raise ConfigError('Port must be an int.') from e

        try:
            _node_id = int(self.config_request.get(
                section, 'node_id', 2))
        except ValueError as e:
            raise ConfigError('Node id must be an int.') from e

        try:
            _encoder_ratio = int(self.config_request.get(
                section, 'encoder_ratio', 1000))
        except ValueError as e:
            raise ConfigError('Encoder ratio must be an int.') from e

        return ModbusBackend.modbusDeviceConfig(_device, _port, _node_id,
                {'encoder_ratio': _encoder_ratio,})

    def _state_watcher(self, master, config, device):
        while not master.watch.is_set():
            try:
                if master.connected.is_set():
                    master.get_command(target=device)
                    if master.block_event.is_set():
                        master.set_command(drive_enable=0, target=device)
                    elif master.auto_enable is True and \
                            master.command['drive_enable'] is False:
                        master.set_command(drive_enable=1, target=device)
                    master.get_status(target=device)
                    master.get_speed(target=device)
                    master.get_velocity(target=device)
                    master.get_encoder_position(target=device)
                    master.get_effort(target=device)
                    master.get_drive_temperature(target=device)
                    try:
                        master.block_event.clear()
                    except AttributeError:
                        pass
                else:
                    try:
                        master.lg.warn('%s: device not connected.' %
                                device.host)
                        master.block_event.set()
                    except AttributeError:
                        pass
                    master.connected.wait(5)
            except ModbusMasterError as e:
                master.lg.warn('State watcher got %s' % repr(e))

            master.watch.wait(ModbusBackend.watcher_interval)

        master.set_speed(0, target=device)
        master.set_command(drive_enable=0, target=device)

    def get_command(self, **kwargs):
        command_set = self._get_comms_set(self.read_comm,
                (self.netdata['command'],), **kwargs)
        if command_set is -1:
            return False

        for command in command_set:
            command = self._to_bools(command[0]+command[1])
            command.reverse()

            for k, v in zip(self.command_keys, command):
                self.command[k] = bool(int(v))

            yield self.command

    def set_command(self, check=True, **kwargs):
        new_cmd = [False,]*32
        for i, k in enumerate(self.command_keys):
            if k in kwargs.keys():
                v = bool(kwargs[k])
            else:
                v = self.command[k]
            new_cmd[i] = (v)

        new_cmd = self._from_bools(new_cmd)
        rtn = self.write_comm(self.netdata['command'], new_cmd, **kwargs)
        if rtn is -1:
            return False

        if check:
            return self.get_command()
        return rtn

    def get_status(self, force=False, **kwargs):
        status_set = self._get_comms_set(self.read_comm, (self.netdata['status'],
            force,), **kwargs)
        if status_set is -1:
            return False

        for status in status_set:
            status = self._to_bools(status[0]+status[1])
            status.reverse()

            for k, v in zip(self.status_keys, status):
                self.status[k] = bool(int(v))

            yield self.status

    def get_error_code(self, **kwargs):
        error = self.read_comm(self.netdata['error_code'], **kwargs)
        self.error_code = self._to_int(error[0]+error[1])

        return self.error_code

    def _get(self, key, format_function=None, **kwargs):
        rtn_set = self._get_comms_set(self.read_comm, (self.netdata[key],), **kwargs)
        if rtn_set is -1:
            return False

        rtn_data = list()
        for rtn in rtn_set:
            if not rtn is None:
                if format_function:
                    rtn_data.append(format_function(rtn[0]+rtn[1]))
                else:
                    rtn_data.append(rtn[0]+rtn[1])
        return rtn_data

    def _set(self, key, value, format_function, check=None, **kwargs):
        rtn_set = self.write_comm(self.netdata[key], format_function(value),
                **kwargs)
        if rtn is -1:
            return False

        if check:
            return self._get(key, check)
        return rtn

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

    def get_speed(self, **kwargs):
        return self.get_float('speed', **kwargs)

    def set_speed(self, new_speed, check=False, **kwargs):
        return self.set_float('speed', new_speed, check, **kwargs)

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
        return self.get_float('encoder_velocity', **kwargs) / self.encoder_ratio

    def get_encoder_position(self, **kwargs):
        return self.get_int('encoder_position', **kwargs)

    def get_follow_error(self, **kwargs):
        return self.get_float('follow_error', **kwargs)

    def get_effort(self, **kwargs):
        return self.get_float('effort', **kwargs)

    def get_drive_temperature(self, **kwargs):
        return self.get_float('drive_temperature', **kwargs)

    def get_dropped_frames(self, **kwargs):
        return self.get_int('dropped_frames', **kwargs)

    def dump_config(self):
        cf = 'dev: %s, port: %s, data_bit: %s, \
world_lenght: %s, reg_by_comms: %s' % \
                (self.device, self.port, self.data_bit,
                self.word_lenght, self.nb_reg_by_comms)
        return cf

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
                rqs.append(self._rq(rq, force, target=t.driver))
            return rqs
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
                rqs.append(self._rq(rq, target=t.driver))
            return rqs
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
                rqs.append(self._rq(rq, target=t.driver))
            return rqs
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
                rqs.append(self._rq(rq, target=t.driver))
            return rqs
        else:
            rq = WriteMultipleRegistersRequest(
                    address, value, unit_id=target.config.node_id)
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
                rqs.append(self._rq(rq, target=t.driver))
            return rqs
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
            response = target.end.execute(rq)
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
            raise ModbusMasterError('Unable to connect to slave', self.lg)


if __name__ == "__main__":
    mb = ModbusBackend(None, None, None, Event())

    mb.word_lenght = 16
    mb.data_bit = 8
    mb.encoder_ratio = 1000
    mb.nb_reg_by_comms = int(mb.word_lenght / mb.data_bit)
    mb.auto_enable = True

    device_config = mb.modbusDeviceConfig('192.168.100.3', 502, 3,
            {'encoder_ratio': 1000,})
    mb.devices_config.append(device_config)
