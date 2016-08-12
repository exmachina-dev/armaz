# -*- coding: utf-8 -*-

from threading import Thread
from threading import Event
from queue import Queue, Empty
from collections import namedtuple
from datetime import datetime
import logging
import functools

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
    _actions = ('ping', 'getitem', 'setitem')

    def __init__(self, *args, **kwargs):
        self._args = args

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
        }
        self._kwargs.update(kwargs)
        self._callback = None

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
            return self._args[0]

    @item.setter
    def item(self, value):
        if self.getitem or self.setitem:
            self._args[0] = value
        else:
            raise KeyError("SlaveRequest doesn't have item.")

    @property
    def args(self):
        if self.getitem or self.setitem:
            return self._args[1:]
        return self._args

    @args.setter
    def args(self, value):
        if self.getitem or self.setitem:
            self._args[1:] = tuple(value)
        else:
            self._args = tuple(value)

    @property
    def kwargs(self):
        return self._kwargs

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, cb):
        self._callback = cb

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
            self.action, ' '.join(self._args), 'with callback' if self.callback is not None else '')


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

        self.running_ev = Event()
        self.newdata_ev = Event()

        self.timeout = float(self.config.get('slave_timeout', .5))
        self.refresh_interval = float(self.config.get('refresh_interval', 0.5))

        self.bridge = Queue()

        self._get_dict = {}
        self._set_dict = {}
        self._latency = None

        self.last_values = {}

        self.errors = 0
        self.max_errors = 10

    def init_driver(self):
        drv = self.slave.driver
        logging.info("Loading %s driver" % drv)
        if drv is not None:
            try:
                driver = Driver().get_driver(drv)
                self.driver = driver(self.driver_config, self.machine)
                self.inlet = self.driver.init_pipes()
            except KeyError:
                logging.error("Unable to get %s driver, aborting." % drv)
                return
            except AbstractDriverError as e:
                raise SlaveMachineError('Unable to intialize driver: %s' % e)
        else:
            logging.error("Machine driver is not defined, aborting.")
            return False

        logging.debug("%s driver loaded" % drv)
        return drv

    def init_pipe(self, outlet):
        pass

    def start(self, loop=False):
        if not loop:
            self._thread = Thread(target=self.loop)
            self._thread.daemon = True

            self._watcher_thread = Thread(target=self.watcher_loop)
            self._watcher_thread.daemon = True

            self.running_ev.clear()
            self.driver.connect()
            self._thread.start()
        else:
            if not self._watcher_thread:
                self.start()

            self._watcher_thread.start()

    def exit(self):
        self.running_ev.set()
        self._watcher_thread.join()
        self._thread.join()
        self.driver.exit()

    def loop(self):
        while not self.running_ev.is_set():
            try:
                recv_item = self.bridge.get(block=True, timeout=2)
                if not isinstance(recv_item, SlaveRequest):
                    logging.error('Unsupported object in queue: %s' % repr(recv_item))
                    continue

                try:
                    if recv_item.getitem:
                        res = self.driver[recv_item.item]
                    elif recv_item.setitem:
                        res = self.driver.__setitem__(recv_item.item, *recv_item.args)
                    else:
                        res = getattr(self.driver, recv_item.attribute)(
                            *recv_item.args)
                    recv_item.callback(res)
                except AttributeError:
                    logging.exception('''Can't find %s in driver''' % recv_item.attribute)
                except SlaveMachineError as e:
                    logging.error('Exception in {n} loop: {e}'.format(
                        n=self.__class__.__name__, e=e))
                except AbstractTimeoutError as e:
                    logging.error('Timeout for {!s}'.format(self))
                except Exception as e:
                    logging.error('Uncatched exception in {n} loop: {e}'.format(
                        n=self.__class__.__name__, e=e))
                self.bridge.task_done()
            except Empty:
                pass

    def watcher_loop(self):
        smode = self.slave.slave_mode
        self.last_values = {}
        self.set_control_mode(smode)
        while not self.running_ev.is_set():
            if SlaveMachine.fatal_event.is_set():
                self.set_to_remote('machine:command:enable', False)
                self.running_ev.wait(self.refresh_interval)
                continue

            try:
                try:
                    for skey in self.SLAVE_MODES[smode]:
                        self._send_if_latest(skey.dest, source=skey.source)
                    self.errors = 0
                except KeyError:
                    raise FatalSlaveMachineError(
                        'Unrecognized mode for slave {!s}: {}'.format(self, smode))
            except AbstractFatalMachineError as e:
                if self.errors > self.max_errors:
                    self.set_to_remote('machine:command:enable', False)
                    if SlaveMachine.fatal_event:
                        SlaveMachine.fatal_event.set()
                    logging.error('Slave machine disabled')
                    continue
                else:
                    self.errors += 1
                logging.error('Fatal exception occured in slave watcher loop '
                              'for {!s}: {!r}'.format(self, e))
            except AbstractMachineError as e:
                logging.error('Exception occured in slave watcher loop '
                              'for {!s}: {!r}'.format(self, e))
            except Exception as e:
                logging.error('Exception in {0} loop: {1}'.format(self.__class__.__name__, e))

            self.running_ev.wait(self.refresh_interval)

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
            request = (yield)

            if not request.setitem:     # Only check if it is a setitem request
                outlet_coro.send(request)
                continue

            if request.dest not in self.SLAVE_MODES[self.slave.slave_mode]:
                continue

            outlet_coro.send(request)

    @coroutine
    def get_value_for_slave(self, outlet_coro):
        while not self.running_event.is_set():
            request = (yield)

            if not request.setitem:     # Only check if it is a setitem request
                outlet_coro.send(request)
                continue

            dest = request.kwargs.get('dest')
            source = request.kwargs.get('source', dest)
            try:
                value = self.machine.machine_keys(self, source)
                if value is None:
                    raise SlaveMachineError('{0} returned None for {1!s}'.format(source, self))

                request.kwargs['value'] = value
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

            value = request.value

            if lvalue is not None and value != lvalue:
                outlet_coro.send(request)
                self.last_values[dest] = value
            else:
                continue

    def _ping_cb(self, start_time, data, event=None):
        rtn = self._default_cb(data, event)

        if rtn:
            dt = datetime.now() - start_time
            self._latency = dt.microseconds / 1000

        if event:
            event.set()

    def _get_cb(self, data, event=None):
        try:
            rtn = self._default_cb(data, event)
            logging.debug('Rtn data: %s' % rtn)
        except SlaveMachineError as e:
            logging.error(repr(e))
            return

        if rtn:
            self._get_dict[rtn.args[1]] = rtn.args[2]
        else:
            raise SlaveMachineError('No data in {}'.format(rtn))

        if event:
            event.set()

    def _set_cb(self, data, event=None):
        try:
            rtn = self._default_cb(data, event)
            logging.debug('Rtn data: %s' % rtn)
        except SlaveMachineError as e:
            logging.error(repr(e))
            return

        if rtn:
            self._set_dict[rtn.args[1]] = rtn.args[2]
        else:
            raise SlaveMachineError('No data in {}'.format(rtn))

        if event:
            event.set()

    def _default_cb(self, data, event=None):
        exc = None
        if isinstance(data, (list, tuple)) and len(data) == 2:
            data, exc = data

        if event and exc and isinstance(exc, Exception):
            event.set()
            raise exc

        if not data:
            if event:
                event.set()
            raise SlaveMachineError('No data')

        if '/ok' in data.path:
            return data
        elif '/error' in data.path:
            e = {
                'path': data.path,
                'args': ' '.join(data.args),
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
