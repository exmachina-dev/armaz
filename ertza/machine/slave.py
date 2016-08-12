# -*- coding: utf-8 -*-

from threading import Thread
from threading import Event
from collections import namedtuple
from datetime import datetime
import logging

from .abstract_machine import AbstractMachine
from .abstract_machine import AbstractMachineError, AbstractFatalMachineError

from ..drivers import Driver
from ..drivers.abstract_driver import AbstractDriverError, AbstractTimeoutError

from ..async_utils import coroutine

logging = logging.getLogger('ertza.machine.slave')

Slave = namedtuple('Slave', ('serialnumber', 'address', 'driver', 'slave_mode', 'config'))
SlaveKey = namedtuple('SlaveKey', ('dest', 'source'))


CONTROL_MODES = {
    'torque':           1,
    'velocity':         2,
    'position':         3,
    'enhanced_torque':  4,
}


class SlaveMachineError(AbstractMachineError):
    pass


class FatalSlaveMachineError(AbstractFatalMachineError):
    fatal_event = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if FatalSlaveMachineError:
            FatalSlaveMachineError.fatal_event.set()
            logging.error('Fatal error, disabling all slaves')


class SlaveRequest(object):
    __slots__ = ('_args', '_action', '_kwargs', '__dict__')
    _actions = ('ping', 'getitem', 'setitem')

    def __init__(self, *args, **kwargs):
        self._args = list(args)

        self._action = None

        for action in SlaveRequest._actions:
            if kwargs.pop(action, False):
                if self.action is not None:
                    raise ValueError('Action already defined for SlaveRequest')
                self.action = action

        self._kwargs = {
            'block': False,
            'event': None,
            'uuid': None,
            'reply': None,
            'exception': None,
            'callback': None,
        }
        self._kwargs.update(kwargs)

        if self.block is True and self._kwargs['event'] is None:
            self._kwargs['event'] = Event()

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, value):
        if value not in SlaveRequest._actions:
            raise ValueError('Unrecognized action')
        self._action = value

    @property
    def item(self):
        if self.getitem or self.setitem:
            try:
                return self._args[0]
            except IndexError:
                return None

    @item.setter
    def item(self, value):
        if self.getitem or self.setitem:
            if len(self._args) < 1:
                self._args.append(value)
            else:
                self._args[0] = value
        else:
            raise KeyError("SlaveRequest doesn't have item.")

    @property
    def args(self):
        return self._args

    @args.setter
    def args(self, value):
        if self.getitem or self.setitem:
            self._args[1:] = list(value)
        else:
            self._args = list(value)

    @property
    def kwargs(self):
        return self._kwargs

    @property
    def reply(self):
        return self._kwargs['reply']

    @reply.setter
    def reply(self, value):
        self._kwargs['reply'] = value
        if self.callback is not None:
            self.callback(self)
        if self.event is not None:
            self.event.set()

    def __getattr__(self, name):
        try:
            if name in SlaveRequest._actions:
                if name == self.action:
                    return True
                return False

            return self._kwargs[name]
        except KeyError:
            return False

    def __repr__(self):
        return 'RQ {} {} {}'.format(
            self.action, ' '.join(map(str, self._args)),
            'with callback' if self.callback is not None else '')


class SlaveMachine(AbstractMachine):

    machine = None
    fatal_event = None

    SLAVE_MODES = {
        'torque': (
            SlaveKey('machine:torque_ref', 'machine:torque'),
            SlaveKey('machine:torque_rise_time', 'machine:torque_rise_time'),
            SlaveKey('machine:torque_fall_time', 'machine:torque_fall_time'),
        ),
        'enhanced_torque': (
            SlaveKey('machine:torque_ref', 'machine:current_ratio'),
            SlaveKey('machine:velocity_ref', 'machine:velocity'),
            SlaveKey('machine:torque_rise_time', None),
            SlaveKey('machine:torque_fall_time', None),
        ),
        'velocity': (
            SlaveKey('machine:velocity_ref', 'machine:velocity'),
            SlaveKey('machine:acceleration', None),
            SlaveKey('machine:deceleration', None),
        ),
    }

    def __init__(self, slave):

        self.config = slave.config
        self.driver = None

        self.slave = slave

        self.driver_config = {
            'target_address': self.slave.address,
            'target_port': int(self.config.get('reply_port', 6969)),
            'timeout': float(self.config.get('slave_timeout', .5)),
        }

        self.timeout = float(self.config.get('slave_timeout', .5))
        self.refresh_interval = float(self.config.get('refresh_interval', 0.5))

        self.inlet = self.outlet = None

        self._get_dict = {}
        self._set_dict = {}
        self._latency = None

        self.last_values = {}

        self._errors = 0
        self.max_errors = 10

        self.running_event = Event()
        self.timeout_event = Event()
        self.fault_event = Event()
        self.watchdog_event = Event()

        self._watchdog_thread = None

    def init_driver(self):
        drv = self.slave.driver
        logging.info("Loading %s driver" % drv)
        if drv is not None:
            try:
                driver = Driver().get_driver(drv)
                self.driver = driver(self.driver_config, self.machine)
                self.init_pipes()
            except KeyError:
                logging.error("Unable to get %s driver, aborting." % drv)
                return
            except AbstractDriverError as e:
                raise SlaveMachineError('Unable to intialize driver: %s' % e)
        else:
            logging.error("Machine driver is not defined, aborting.")
            return False

        logging.debug('{} driver loaded: {!s}'.format(drv, self.driver))

    def init_pipes(self):
        self.driver.init_pipes()
        self.outlet = self.filter_by_operating_mode(
            self.get_value_for_slave(
                self.send_if_latest(self.driver.outlet)))
        self.inlet = self.driver.inlet

    def start(self, **kwargs):
        self.running_event.clear()
        self.driver.connect()

        if kwargs.get('watchdog', True):
            self.start_watchdog()

    def start_watchdog(self):
        if self._watchdog_thread:
            self.watchdog_event.set()
            self._watchdog_thread.join()

        self.watchdog_event.clear()
        self._watchdog_thread = Thread(target=self._watchdog)
        self._watchdog_thread.daemon = True
        self._watchdog_thread.start()

    def exit(self):
        self.running_event.set()
        self.driver.exit()

    def enslave(self):
        self.driver.set('machine:operating_mode', 'slave', self.machine.get_address(self.slave.driver))

    @property
    def infos(self):
        rev = self.driver['machine:revision']
        try:
            var = self.driver['machine:variant'].split('.')
        except AttributeError:
            var = 'none:none'

        return (self.serialnumber, var[0].upper(), var[1].upper(), rev)

    @property
    def serialnumber(self):
        return self.slave.serialnumber

    @property
    def errors(self):
        return self._errors

    @property
    def forward_keys(self):
        return self.SLAVE_MODES[self.slave.slave_mode]

    def get_serialnumber(self):
        return self.get('machine:serialnumber', block=True)

    def ping(self, block=True):
        try:
            start_time = datetime.now()
            ev = Event() if block else None
            rq = self.driver.ping(block=block, event=ev)
            if not rq.path.endswith('/ok'):
                raise SlaveMachineError('Unexpected reply while pinging: {}'
                                        .format(rq.path))
            time_delta = datetime.now() - start_time
            self._latency = time_delta.microseconds / 1000
            return self._latency
        except AbstractTimeoutError as e:
            raise SlaveMachineError('Timeout while pinging: {}!s'.format(e))

    def set_control_mode(self, mode):
        if mode not in CONTROL_MODES.keys():
            raise KeyError('Unexpected mode: {0}'.format(mode))

        return self.set('machine:command:control_mode', CONTROL_MODES[mode], block=True)

    def get(self, key, **kwargs):
        return self.driver.get(key, **kwargs)

    def set(self, key, *args, **kwargs):
        return self.driver.set(key, *args, **kwargs)

    @coroutine
    def filter_by_operating_mode(self, outlet_coro):
        while not self.running_event.is_set():
            try:
                request = (yield)

                if not request.setitem:     # Only check if it is a setitem request
                    outlet_coro.send(request)
                    continue

                key = SlaveKey(request.dest, request.source)
                if key not in self.SLAVE_MODES[self.slave.slave_mode]:
                    continue

                outlet_coro.send(request)
            except StopIteration:
                self.running_event.set()
                break

    @coroutine
    def get_value_for_slave(self, outlet_coro):
        while not self.running_event.is_set():
            request = (yield)

            if not request.setitem:     # Only check if it is a setitem request
                outlet_coro.send(request)
                continue

            dest = request.kwargs.get('dest')
            source = request.kwargs.get('source') or dest
            try:
                value = self.machine.machine_keys.get_value_for_slave(self, source)

                if value is None:
                    raise SlaveMachineError('{0} returned None for {1!s}'.format(source, self))

                request.item = dest
                request.args = value,
                outlet_coro.send(request)
            except SlaveMachineError as e:
                logging.warn('Exception in {0!s}: {1!s}'.format(self, e))
            except AbstractMachineError:
                logging.warn('Machine is not ready')
            except Exception as e:
                logging.exception('Exception in {0!s}: {1!s}'.format(self, e))
                raise SlaveMachineError('{!s}'.format(e))

    @coroutine
    def send_if_latest(self, outlet_coro):
        while not self.running_event.is_set():
            request = (yield)

            if not request.setitem:     # Only check if it is a setitem request
                outlet_coro.send(request)
                continue

            dest = request.kwargs.get('dest')
            lvalue = self.last_values.get(dest, None)

            value = request.args[1]

            if value != lvalue:
                outlet_coro.send(request)
                self.last_values[dest] = value
            else:
                continue

    def _watchdog(self):
        while not self.watchdog_event.is_set():
            if self.fatal_event.is_set() or self.fault_event.is_set():
                self.set('machine:command:enable', False)

            self.watchdog_event.wait(self.refresh_interval)

    def _get_cb(self, rq):
        try:
            rtn = self._default_cb(rq)
            logging.debug('Rtn data: %s' % rtn)
        except SlaveMachineError as e:
            logging.error(repr(e))
            return

        if rtn:
            self._get_dict[rtn.args[1]] = rtn.args[2]
        else:
            raise SlaveMachineError('No data in {}'.format(rtn))

    def _set_cb(self, rq):
        try:
            rtn = self._default_cb(rq)
            logging.debug('Rtn data: %s' % rtn)
        except SlaveMachineError as e:
            logging.error(repr(e))
            return

        if rtn:
            self._set_dict[rtn.args[1]] = rtn.args[2]
        else:
            raise SlaveMachineError('No data in {}'.format(rtn))

    def _default_cb(self, rq):
        print('def_cb', rq)
        if rq.exception is not None:
            raise rq.exception

        if rq.reply is None:
            raise SlaveMachineError('No data')

        if '/ok' in rq.reply.path:
            return rq.reply.args
        elif '/error' in rq.reply.path:
            e = {
                'path': rq.reply.path,
                'args': ' '.join(rq.reply.args),
            }
            raise SlaveMachineError('Got error in {path}: {args}'.format(**e))

    def __repr__(self):
        i = {
            'name': self.__class__.__name__,
            'addr': self.slave.address,
            'port': self.driver_config['target_port'],
            'prot': self.slave.driver,
            'serial': self.slave.serialnumber,
            'mode': self.slave.slave_mode,
        }
        return '{name}: {addr}:{port} via {prot} ({serial}) in {mode} mode'.format(**i)

    def __str__(self):
        i = {
            'addr': self.slave.address,
            'port': self.driver_config['target_port'],
            'prot': self.slave.driver.lower(),
            'serial': self.slave.serialnumber,
        }
        return '{addr}:{port} via {prot} ({serial})'.format(**i)
