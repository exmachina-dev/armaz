# -*- coding: utf-8 -*-

from time import sleep
from collections import namedtuple, OrderedDict

from multiprocessing import Event

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import pymodbus.exceptions as pmde

from .MicroFlexE100 import MicroFlexE100Backend

from ...config import ConfigRequest
from ...errors import ConfigError, ModbusMasterError
from ...utils import retry


ModbusDevice = namedtuple('ModbusDevice', ['config', 'driver', 'watcher'])
ModbusDeviceConfig = namedtuple('ModbusDeviceConfig', ['host', 'port',
'node_id', 'motor_config'])
ModbusDeviceDriver = namedtuple('ModbusDeviceDriver', ['config', 'state',
    'end'])


class ModbusBackend(MicroFlexE100Backend):
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
            'timeout':              22,
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

    ModbusDeviceState = namedtuple('ModbusDeviceState', netdata.keys())

    watcher_interval = 0.01


    def __init__(self, config, logger, restart_event, block_event=None,
            **kwargs):
        self.errorcode = None
        self.end = None
        self.config_request = None
        self.max_retry = 5
        self.retry = self.max_retry
        self.restart_init_delay = 10
        self.restart_delay = 10
        self.restart_backoff = 2

        if 'connected_event' in kwargs:
            self.connected = kwargs['connected_event']
        else:
            self.connected = Event()

        if 'watch_event' in kwargs:
            self.watch = kwargs['watch_event']
        else:
            self.watch = Event()

        self.devices = list()
        self.devices_config = list()
        self.devices_state = self.ModbusDeviceState(
                *[{} for i in range(len(self.netdata))])

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
                    self.connect_device(d)

                self.lg.debug('Starting modbus watchers.')

                self.connected.set()
                for d in self.devices:
                    if not d.driver.state['connected']:
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
                raise ModbusMasterError('Unable to connect to slave: %s' % e)
                self.connected.clear()

    def close(self):
        self.set_speed(0)
        self.set_command(drive_enable=0)
        for d in self.devices:
            d.watcher['watch'] = False
            d.driver.end.close()

        self.connected.clear()

    def reconnect(self):
        if self.connected.is_set():
            self.close()
        self.get_config()
        self.connect()

    def create_devices(self):
        for i, _c in enumerate(self.devices_config):
            self.lg.debug('Creating %s:%s:%s device.' % (_c.host, _c.port,
                _c.node_id))
            _driver = ModbusClient(host=_c.host, port=_c.port)
            _d = ModbusDeviceDriver(_c,
                    state={'connected': False,}, end=_driver)

            _w = {'config': _c, 'watch': True,}

            self.devices.append(ModbusDevice( _c, _d, _w))
            for s in self.devices_state:
                s[_c.host] = None

            self.devices_state.command[_c.host] = {}
            self.devices_state.status[_c.host] = {}
            #for k in self.command_keys:
            #    self.devices_state[_c.host].command[k] = None
            #for k in self.status_keys:
            #    self.devices_state[_c.host].status[k] = None

    def connect_device(self, device):
        if device.driver.end.connect():
            device.driver.state['connected'] = True
            return True

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

        return ModbusDeviceConfig(_device, _port, _node_id,
                {'encoder_ratio': _encoder_ratio,})

    def state_watcher(self):
        for device in self.devices:
            if not device.watcher['watch']:
                return False

        try:
            if self.connected.is_set():
                self.update_state()

                if self.block_event.is_set():
                    self.set_speed(0)
                    self.set_command(drive_enable=0)
                else:
                    for device in self.devices:
                        if self.can_be_enabled(device.config.host) is True:
                            self.set_speed(0, target=device)
                            self.set_command(drive_enable=1,
                                    target=device)
                try:
                    self.block_event.clear()
                except AttributeError:
                    pass
            else:
                try:
                    for device in self.devices:
                        if self.connect_device(device):
                            self.connected.set()
                        else:
                            self.lg.warn('%s device not connected.' %
                                    device.config.host)
                            self.connected.clear()
                            self.block_event.set()
                except AttributeError:
                    self.lg.warn(
                            'Block event does not exist. Unable \
                            to block all devices.')
                self.connected.wait(5)
        except ModbusMasterError as e:
            for d in self.devices:
                d.driver.state['connected'] = False
            self.lg.warn('State watcher got %s' % repr(e))

    def can_be_enabled(self, host):
        try:
            if self.devices_state.status[host]['drive_enable'] is True:
                return False
            if self.devices_state.status[host]['drive_enable_ready'] is not True:
                return False
            if self.devices_state.command[host]['drive_cancel'] is True:
                return False
        except KeyError as e:
            self.lg.warn('Unable to get status: %s' % repr(e))
            return False

        return True

    def update_state(self, target='all'):
        new_state = tuple(self._update_state())
        chk_state = list()
        for st in new_state:
            if not type(st) is dict:
                chk_state.append({})
            else:
                chk_state.append(st)

        new_state = self.ModbusDeviceState(*chk_state)
        self.devices_state = new_state
        if target is 'all':
            for d in self.devices:
                self._reset_timeout(target=d)
        else:
            self._reset_timeout(target=target)
            
    def _update_state(self):
        for nd in self.netdata.keys():
            if 'status' in nd or 'command' in nd:
                t = dict
            else:
                t = int
            yield t, getattr(self, 'get_%s' % nd)()

    def _reset_timeout(self, target):
        h = target.config.host
        d = target

        try:
            t = bool(self.devices_state.timeout[h])
            self.set_timeout(not t, target=d)
        except KeyError:
            pass

    def dump_config(self):
        cf = 'dev: %s, port: %s, data_bit: %s, \
world_lenght: %s, reg_by_comms: %s' % \
                (self.device, self.port, self.data_bit,
                self.word_lenght, self.nb_reg_by_comms)
        return cf

    def __del__(self):
        self.close()


if __name__ == "__main__":
    mb = ModbusBackend(None, None, None, Event())

    mb.word_lenght = 16
    mb.data_bit = 8
    mb.encoder_ratio = 1000
    mb.nb_reg_by_comms = int(mb.word_lenght / mb.data_bit)
    mb.auto_enable = True

    device_config = ModbusDeviceConfig('192.168.100.2', 502, 2,
            {'encoder_ratio': 1000,})
    mb.devices_config.append(device_config)
    device_config = ModbusDeviceConfig('192.168.100.3', 502, 3,
            {'encoder_ratio': 1000,})
    mb.devices_config.append(device_config)
