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


Slave = namedtuple('Slave', ('serialnumber', 'address', 'driver', 'config'))


class SlaveMachineError(AbstractMachineError):
    pass


class SlaveMachine(AbstractMachine):

    machine = None

    class _Request(object):
        def __init__(self, attr, *args, **kwargs):
            if 'getitem' in kwargs and kwargs['getitem']:
                self._item = attr
                self._attr = None
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

    def __init__(self, slave):

        self.config = slave.config
        self.driver = None

        self.slave = slave

        self.driver_config = {
            'target_address': self.slave.address,
            'target_port': int(self.config.get('reply_port', 6969)),
        }

        self._thread = Thread(target=self.loop)
        self._thread.daemon = True

        self.running_ev = Event()
        self.newdata_ev = Event()

        self.timeout = 2.0

        self.bridge = Queue()

        self._get_dict = {}
        self._set_dict = {}

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
        self.running_ev.clear()
        self.driver.connect()
        self._thread.start()

        self.ping()

    def exit(self):
        self.running_ev.set()
        self._thread.join()
        self.driver.exit()

    def loop(self):
        try:
            while not self.running_ev.is_set():
                recv_item = self.bridge.get(block=True, timeout=2)
                if not isinstance(recv_item, self._Request):
                    logging.error('Unsupported object in queue: %s' % repr(recv_item))
                    continue

                try:
                    logging.debug('Executing from queue: %s' % repr(recv_item))
                    print(recv_item.getitem)
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
                self.bridge.task_done()
        except Empty:
            pass

    def request_from_remote(self, callback, attribute, *args, **kwargs):
        event = kwargs.pop('event', None)
        rq = self._Request(attribute, *args, **kwargs)
        if event:
            callback = functools.partial(callback, event=event)

        rq.set_callback(callback)

        self.bridge.put(rq)
        return rq

    def ping(self):
        try:
            def _cb(data):
                dt = datetime.now() - data[1]
                print(dt.microseconds / 1000)
                print(data)

            return self.request_from_remote(_cb, 'ping', block=False)

        except AbstractDriverError as e:
            raise SlaveMachineError('Unable to ping remote machine: %s' % e)

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
        return self.request_from_remote(self._get_cb,
                                        'machine:serialnumber', getitem=True)

    def get_from_remote(self, key, **kwargs):
        print(kwargs)
        ev = Event() if 'block' in kwargs and kwargs['block'] is True else None
        print(ev)
        rq = self.request_from_remote(self._get_cb, key, getitem=True, event=ev)

        if ev and ev.wait(self.timeout):
            return self._get_dict[key]
        return rq

    def set_to_remote(self, key, *args, **kwargs):
        ev = Event() if 'block' in kwargs and kwargs['block'] is True else None

        rq = self.request_from_remote(self._set_cb, key, *args, setitem=True, event=ev)

        if ev and ev.wait(self.timeout):
            return self._set_dict[key]
        return rq

    def _get_cb(self, data, event=None):
        if '/ok' in data.path:
            self._get_dict[data.args[0]] = data.args[1]
        elif '/error' in data.path:
            e = {
                'path': data.path,
                'args': ' '.join(data.args),
            }
            raise SlaveMachineError('Got error in {path}: {args}'.format(**e))

        if event:
            event.set()
            print('Event set')
        print(data)

    def _set_cb(self, data, event=None):
        if '/ok' in data.path:
            self._set_dict[data.args[0]] = data.args[1]
        elif '/error' in data.path:
            e = {
                'path': data.path,
                'args': ' '.join(data.args),
            }
            raise SlaveMachineError('Got error in {path}: {args}'.format(**e))

        if event:
            event.set()
            print('Event set')
        print(data)

    def __repr__(self):
        i = {
            'name': self.__class__.__name__,
            'addr': self.slave.address,
            'port': self.driver_config['target_port'],
            'prot': self.slave.driver,
            'serial': self.slave.serialnumber,
        }
        return '{name}: {addr}:{port} via {prot} ({serial})'.format(**i)
