# -*- coding: utf-8 -*-

from threading import Thread
from threading import Event
from queue import Queue, Empty
from collections import namedtuple
from datetime import datetime
import logging
import functools

from ertza.machine.AbstractMachine import AbstractMachine, AbstractMachineError

from ertza.drivers.Drivers import Driver
from ertza.drivers.AbstractDriver import AbstractDriverError

logging = logging.getLogger(__name__)

Slave = namedtuple('Slave', ('serialnumber', 'address', 'driver', 'slave_mode', 'config'))


CONTROL_MODES = {
    'torque':           1,
    'velocity':         2,
    'position':         3,
    'enhanced_torque':  4,
}


FatalEvent = Event()


class SlaveMachineError(AbstractMachineError):
    pass


class FatalSlaveMachineError(SlaveMachineError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        FatalEvent.set()
        logging.error('Fatal error, disabling all slaves')


class SlaveRequest(object):
    def __init__(self, attr, *args, **kwargs):
        self._args = ()
        self._attr = None
        if 'getitem' in kwargs and kwargs['getitem']:
            self._item = attr
        elif 'setitem' in kwargs and kwargs['setitem']:
            self._item = attr
            self._args = args
        else:
            self._attr = attr
            self._args = args

        self._kwargs = {
            'getitem': False,
            'setitem': False,
        }
        self._kwargs.update(kwargs)
        self._callback = None

    def set_callback(self, cb):
        self._callback = cb

    @property
    def attribute(self):
        return self._attr

    @property
    def item(self):
        return self._item

    @property
    def args(self):
        return self._args

    @property
    def kwargs(self):
        return self._kwargs

    @property
    def callback(self):
        return self._callback

    def __getattr__(self, name):
        return self._kwargs[name]

    def __repr__(self):
        return '{} {} {} {}'.format('RQ', self.attribute,
                                    ' '.join(self.args), self.callback)


class SlaveMachine(AbstractMachine):

    machine = None

    def __init__(self, slave):

        self.config = slave.config
        self.driver = None

        self.slave = slave

        self.driver_config = {
            'target_address': self.slave.address,
            'target_port': int(self.config.get('reply_port', 6969)),
        }

        self.running_ev = Event()
        self.newdata_ev = Event()

        self.timeout = float(self.config.get('slave_timeout', 2.0))
        self.refresh_interval = float(self.config.get('refresh_interval', 0.5))

        self.bridge = Queue()

        self._get_dict = {}
        self._set_dict = {}
        self._latency = None

        self.last_values = {}

    def init_driver(self):
        drv = self.slave.driver
        logging.info("Loading %s driver" % drv)
        if drv is not None:
            try:
                driver = Driver().get_driver(drv)
                self.driver = driver(self.driver_config, self.machine)
                self.inlet = self.driver.init_queue()
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

    def start(self):
        self._thread = Thread(target=self.loop)
        self._thread.daemon = True

        self._watcher_thread = Thread(target=self.watcher_loop)
        self._watcher_thread.daemon = True

        self.running_ev.clear()
        self.driver.connect()
        self._thread.start()
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
            if FatalEvent.is_set():
                self.set_to_remote('machine:command:enable', False)
                self.running_ev.wait(self.refresh_interval)
                continue

            try:
                if smode == 'torque':
                    self._send_if_latest('machine:torque_ref', source='machine:torque')
                    self._send_if_latest('machine:torque_rise_time', source='machine:torque_rise_time')
                    self._send_if_latest('machine:torque_fall_time', source='machine:torque_fall_time')
                elif smode == 'enhanced_torque':
                    self._send_if_latest('machine:torque_ref', source='machine:current_ratio')
                    self._send_if_latest('machine:velocity_ref', source='machine:velocity')
                    self._send_if_latest('machine:torque_rise_time')
                    self._send_if_latest('machine:torque_fall_time')
                elif smode == 'velocity':
                    self._send_if_latest('machine:velocity_ref', source='machine:velocity')
                    self._send_if_latest('machine:acceleration')
                    self._send_if_latest('machine:deceleration')
            except Exception as e:
                self.set_to_remote('machine:command:enable', False)
                logging.error('Exception in {0} loop: {1}'.format(self.__class__.__name__, e))
                logging.error('Slave machine disabled')

            self.running_ev.wait(self.refresh_interval)

    def request_from_remote(self, callback, attribute, *args, **kwargs):
        event = kwargs.pop('event', None)
        rq = SlaveRequest(attribute, *args, **kwargs)
        if event:
            callback = functools.partial(callback, event=event)

        rq.set_callback(callback)

        self.bridge.put(rq)
        return rq

    def enslave(self):
        self.set_to_remote('machine:operation_mode', 'slave', self.machine.address)

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
        return self.get_from_remote('machine:serialnumber', block=True)

    def ping(self, block=True):
        ev = Event() if block is True else None

        start_time = datetime.now()
        cb = functools.partial(self._ping_cb, start_time)
        rq = self.request_from_remote(cb, 'ping', event=ev)

        if ev is not None and ev.wait(self.timeout):
            return self._latency
        return rq

    def get_from_remote(self, key, **kwargs):
        ev = Event() if 'block' in kwargs and kwargs['block'] is True else None

        rq = self.request_from_remote(self._get_cb, key, getitem=True, event=ev)

        if ev is not None and ev.wait(self.timeout):
            return self._get_dict[key]
        return rq

    def set_to_remote(self, key, *args, **kwargs):
        ev = Event() if 'block' in kwargs and kwargs['block'] is True else None

        rq = self.request_from_remote(self._set_cb, key, *args, setitem=True, event=ev)

        if ev is not None and ev.wait(self.timeout):
            return self._set_dict[key]
        return rq

    def set_control_mode(self, mode):
        if mode not in CONTROL_MODES.keys():
            raise KeyError('Unexpected mode: {0}'.format(mode))

        return self.set_to_remote('machine:command:control_mode', CONTROL_MODES[mode], block=True)

    def _send_if_latest(self, dest, source=None):
        source = source or dest
        lvalue = self.last_values.get(dest, None)

        if not self.machine.machine_keys:
            logging.warn('Machine keys not found')
            return

        try:
            value = self.machine.machine_keys.get_value_for_slave(self, source)

            if value is None:
                raise SlaveMachineError('{0} returned None for {1!s}'.format(source, self))
        except SlaveMachineError as e:
            logging.warn('Exception in {0!s}: {1!s}'.format(self, e))
        except AbstractMachineError:
            logging.warn('Machine is not ready')
        except Exception as e:
            logging.exception('Exception in {0!s}: {1!s}'.format(self, e))
            raise SlaveMachineError('{!s}'.format(e))

        if lvalue:
            if value != lvalue:
                self.set_to_remote(dest, value)
                self.last_values[dest] = value
        else:
            self.set_to_remote(dest, value)
            self.last_values[dest] = value

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
