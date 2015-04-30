# -*- coding: utf-8 -*-

from time import sleep
from collections import namedtuple, OrderedDict

from multiprocessing import Process, Event

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import pymodbus.exceptions as pmde

from .MicroFlexE100 import MicroFlexE100Backend

from ...config import ConfigRequest
from ...errors import ConfigError, ModbusMasterError
from ...utils import retry


class ModbusBackend(MicroFlexE100Backend):
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
    netdata = OrderedDict(sorted(netdata.items(), key=lambda t: t[1]))

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

    modbusDeviceState = OrderedDict.fromkeys(netdata.keys())

    watcher_interval = 0.01


    def __init__(self, config, logger, restart_event, block_event=None,
            **kwargs):
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
        self.devices_state = {}

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
                        self.lg.warn('%s not connected.' % d.config.host)

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
            self.devices_state[_c.host] = OrderedDict.fromkeys(
                    ModbusBackend.netdata.keys())
            #for k in self.command_keys:
            #    self.devices_state[_c.host].command[k] = None
            #for k in self.status_keys:
            #    self.devices_state[_c.host].status[k] = None

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
                    master.update_state(target=device)

                    if master.block_event.is_set():
                        #master.set_command(drive_enable=0, target=device)
                        pass
                    elif master.can_be_enabled(device.config.host) is True:
                        master.set_command(drive_enable=1, target=device)

                    print(config.host)
                    print(self.devices_state[config.host])
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

    def can_be_enabled(self, host):
        if self.devices_state[host]['status']['drive_enable'] is True:
            return False
        if self.devices_state[host]['status']['drive_enable_ready'] is not True:
            return False
        if self.devices_state[host]['command']['drive_cancel'] is True:
            return False
        return True

    def update_state(self, target='all'):
        if target == 'all':
            for d in self.devices:
                self._update_state(target=d)
        else:
            self._update_state(target=target)
            
    def _update_state(self, target):
        h = target.config.host
        self.devices_state[h]['command'] = self.get_command(target=target)[h]
        self.devices_state[h]['status'] = self.get_status(target=target)[h]
        self.devices_state[h]['error_code'] = self.get_error_code(target=target)[h]
        self.devices_state[h]['speed'] = self.get_speed(target=target)[h]
        self.devices_state[h]['acceleration'] = self.get_acceleration(target=target)[h]
        self.devices_state[h]['deceleration'] = self.get_deceleration(target=target)[h]
        self.devices_state[h]['velocity'] = self.get_velocity(target=target)[h]
        self.devices_state[h]['encoder_velocity'] = \
                self.get_encoder_velocity(target=target)[h] / \
                target.config.motor_config['encoder_ratio']
        self.devices_state[h]['encoder_position'] = self.get_encoder_position(target=target)[h]
        self.devices_state[h]['follow_error'] = self.get_follow_error(target=target)[h]
        self.devices_state[h]['effort'] = self.get_effort(target=target)[h]
        self.devices_state[h]['drive_temperature'] = self.get_drive_temperature(target=target)[h]
        self.devices_state[h]['dropped_frames'] = self.get_dropped_frames(target=target)[h]

    def dump_config(self):
        cf = 'dev: %s, port: %s, data_bit: %s, \
world_lenght: %s, reg_by_comms: %s' % \
                (self.device, self.port, self.data_bit,
                self.word_lenght, self.nb_reg_by_comms)
        return cf


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
