# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""

"""
import sys
import time
import logging

from threading import Event, Thread, Lock

from ..processors.osc.message import OscMessage
from ..machines.machine import Machine
from ..machines.slave import SlaveMachineError, FatalSlaveMachineError, SlaveRequest

from ..drivers.utils import retry

from ..configparser import parameter as _p

from .filters import Filter
from .exceptions import MotionError, FatalMotionError

logging = logging.getLogger('ertza.motion')


class Channel(object):
    _Channels = {}
    _Lock = Lock()

    def __init__(self, name, callback):
        if name in self._Channels:
            raise ValueError('Name already exists')

        self._name = name
        self._callback = callback
        with self._Lock:
            self._Channels[self.name] = {
                'ids': [],
                'objs': {},
            }

    def suscribe(self, obj):
        if id(obj) in self.obj_ids:
            raise ValueError('Object already subscribed.')

        with self._Lock:
            self.obj_ids.append(id(obj))
            self.objs[id(obj)] = obj

    def unsuscribe(self, obj):
        with self._Lock:
            if id(obj) not in self.obj_ids:
                raise ValueError('Object not found.')

            self.obj_ids.remove(id(obj))
            self.objs.pop(id(obj))

    def send(self, message):
        with self._Lock:
            objs = list(self.objs.values())

        for obj in objs:
            try:
                obj.send(message, callback=self.callback)
            except Exception:
                raise

    def close(self, end_message):
        pass

    @property
    def name(self):
        return self._name

    @property
    def callback(self):
        return self._callback

    @property
    def obj_ids(self):
        return self._Channels[self.name]['ids']

    @property
    def objs(self):
        return self._Channels[self.name]['objs']


class MotionUnit(object):
    def __init__(self, *args, **kwargs):
        # AbstractMachine.MOTIONSERVER = self

        self.fatal_event = Event()

        self.version = None

        self.config = None

        self.cape_infos = None
        self.ethernet_interface = None

        self.comms = {}
        self.processors = {}
        self.commands = None
        self.synced_commands = None
        self.unbuffered_commands = None

        self.machines = {}
        self.alive_machines = {}
        # self.machines_channel = Channel('machines', self._machines_cb)
        # self._machines_thread = None

        # self._machine_keys = None

        # self._profile_parameters = {
        #     'ip_address': _p(str, None, self.set_ip_address),
        #     'operating_mode': _p(str, None, self.set_operating_mode),
        # }

        self._last_command_time = time.time()
        self._running_event = Event()
        self._timeout_event = Event()

        self.slave_refresh_interval = 1

        self.remotes = {}
        self.switch_callback = self._switch_cb
        self.switch_states = {}

        self.target_filters = list()

    def start(self):
        self.register_filter(alias_mask='/identify', protocol='OSC', exclusive=True, is_reply=True,
                             target=self.update_alive_machines, args_length=2)
        self.discover_machines()

    def stop(self):
        "Stop all machines and motion server"

        self._running_event.set()

        if self.machines:
            for m in self.machines.values():
                m.exit()

    def handle(self, *args, **kwargs):
        """
        Filter a message coming from a processor, apply filters
        and decide what to do
        """
        m, p = args
        f = self.target_filters

        for f in self.target_filters:
            if f.accepts(m, p):
                f.handle(m, p)
                logging.debug('%s handled by %s', repr(m), str(f))
                if f.is_exclusive:
                    return

        p.execute(m)

    def discover_machines(self):
        """
        Send a identify request to broadcast.
        """

        self.alive_machines = {}
        m = OscMessage('/identify', hostname='255.255.255.255')
        self.send_message(m)

    def update_alive_machines(self, m):
        if len(m.args) != 2:
            return False
        sn, ip = m.args
        ip, pt = ip.split(':')
        if '/' in ip:
            ip, nm = ip.split('/')
        else:
            nm = None

        self.alive_machines[(sn, ip,)] = {
            'serialnumber': sn,
            'ip_address': ip,
            'port': pt,
            'cidr': nm,
        }

        self.register_machine(sn, ip)

    def register_filter(self, new_filter=None, **kwargs):
        if new_filter:
            if not isinstance(new_filter, Filter):
                raise TypeError('Unexpected type %s for new_filter' % type(new_filter))
        else:
            new_filter = Filter(**kwargs)

        self.target_filters.append(new_filter)

    def register_machine(self, sn=None, ip=None):
        if sn is None and ip is None:
            raise ValueError('sn and ip can\'t be both None')

        alive_keys = list(self.alive_machines.keys())

        sni = None
        ipi = None
        for i, k in enumerate(alive_keys):
            if sn and sn == k[0]:
                sni = i

            if ip and ip == k[1]:
                ipi = i

        i = sni or ipi
        if i is None:
            raise KeyError('Machine not found')
        m = self.alive_machines[alive_keys[i]]

        asn, aip = alive_keys[i]

        machine = Machine(**m)
        # Redirect all trafic from this machine to its Machine
        self.register_filter(sender=aip, target=machine.handle, exclusive=True)
        self.machines[(asn, aip,)] = machine


    def start_slaves_loop(self):
        if self._slaves_thread is not None:
            self._slaves_running_event.set()
            self._slaves_thread.join()
            self._slaves_thread = None

        self._slaves_running_event.clear()
        self._slaves_thread = Thread(target=self._slaves_loop)
        self._slaves_thread.daemon = True

        self._slaves_thread.start()

    def reply(self, command):
        if command.answer is not None:
            self.send_message(command.protocol, command.answer)

    def send_message(self, msg):
        self.comms[msg.protocol].send_message(msg)

    @property
    def machine_keys(self):
        if not self._machine_keys:
            raise MotionError('No machine keys yet')

        return self._machine_keys

    def get_address(self, driver):
        if driver.lower() is 'osc':
            return self.osc_address
        else:
            return self.ip_address

    def search_machines(self):
        machines_cf = self.config['machines']
        machines = []

        for key, item in machines_cf.items():
            if key.startswith('machine_serialnumber_'):
                machine_id = int(key.split('_')[2])
                machine_sn = item
                machine_ip = machines_cf['machine_address_%d' % machine_id]
                machine_md = machines_cf['machine_mode_%d' % machine_id]
                machine_dv = machines_cf.get('machine_driver_%d' % machine_id,
                                         fallback='osc').title()

                machine_cf = {}
                if self.config.has_section('machine_%s' % machine_sn):
                    machine_cf = self.config['machine_%s' % machine_sn]
                    logging.info('Found config for machine with S/N {}'.format(
                        machine_sn))

                s = Slave(machine_sn, machine_ip, machine_dv, machine_md, machine_cf)
                logging.info('Found {2} machine at {1} '
                             'with S/N {0}'.format(*s))
                machines.append(s)

        if not machines:
            return False

        self.machine_machines = {}
        for s in machines:
            sm = SlaveMachine(s)
            self.machine_machines[(s.serialnumber, s.address)] = sm

        return self.machine_machines

    @retry(SlaveMachineError, 20, 10, 1.5)
    def slave_block_ping(self, sm):
        p = sm.ping()
        if isinstance(p, SlaveRequest):
            raise SlaveMachineError('Unable to ping slave {!r} !'.format(sm))

        if isinstance(p, float):
            return p
        else:
            raise MotionError('Unexpected result while pinging {!s}'.format(sm))

    @retry(MotionError, 5, 5, 2)
    def load_slaves(self):
        if not self.slave_machines:
            if not self.search_slaves():
                logging.info('No slaves found')
                return

        for sm in self.slave_machines.values():
            logging.debug('Initializing {2} slave at {1} ({0})'.format(*sm.slave))
            try:
                self.init_slave(sm)
                ping_time = self.slave_block_ping(sm)
                logging.info('Slave at {2} took {0:.2} ms to respond'.format(
                    ping_time, *sm.slave))
            except AbstractMachineError as e:
                logging.error('Unable to contact {3} slave at {2} ({1}) '
                              '{0}'.format(str(e), *sm.slave))
                return

            sn = sm.get_from_remote('machine:serialnumber', block=True)
            if type(sn) == str and sm.serialnumber != sn:
                infos = sm.slave + (sm.get_serialnumber(),)
                raise MachineError('S/N don\'t match for {2} slave '
                                   'at {1} ({0} vs {4})'.format(*infos))

            else:
                sm.start(loop=True)
                self.slaves_channel.suscribe(sm)

    def add_slave(self, driver, address, mode, conf={}):
        try:
            s = Slave(None, address, driver.title(), mode, conf)
            sm = SlaveMachine(s)
            self.init_slave(sm)
            sm.set_master(self.serialnumber, self.address(driver))
            sm.enslave()
            sm.ping()

            existing_s = self.get_slave(serialnumber=sm.serialnumber)
            if existing_s:
                raise MachineError('Already existing {2} at {1} '
                                   'with S/N {0}'.format(*existing_s.slave))

            self.slaves[(sm.serialnumber, sm.address)] = sm
            s = sm.slave
            logging.info('New {2} slave at {1} '
                         'with S/N {0}'.format(*s))
            return s
        except Exception as e:
            raise MachineError('Unable to add slave: %s' % repr(e))

    def remove_slave(self, sn):
        self._check_operating_mode()

        try:
            sm = self.get_slave(sn)
            if not sm:
                raise MachineError('Slave with S/N %s not found' % sn)

            sm.unslave()
            sm.exit()
            self.slave_machines.pop((sm.slave.serialnumber, sm.slave.address))
        except Exception as e:
            raise MachineError('Unable to remove slave: %s' % str(e))

    def get_slave(self, serialnumber=None, address=None):
        for sn, ad in self.slave_machines.keys():
            if serialnumber == sn:
                return self.slave_machines[(sn, ad)]
            elif address == ad:
                return self.slave_machines[(sn, ad)]
        else:
            if serialnumber is not None:
                logging.error('Unable to find slave by S/N {}'.format(serialnumber))
            else:
                logging.error('Unable to find slave by address {}'.format(address))

        return None

    def init_slave(self, slave_machine):
        try:
            slave_machine.init_driver()
            slave_machine.start()
        except SlaveMachineError as e:
            raise FatalMachineError('Couldn\'t initialize {2} slave at {1} '
                                    'with S/N {0}: {exc}'
                                    .format(*slave_machine.slave, exc=e))

    def set_operating_mode(self, mode=None, **kwargs):
        if mode is None:
            logging.info('Deactivating %s mode' % self.operating_mode)

            if self.operating_mode == 'slave':
                self.free()
            elif self.operating_mode == 'master':
                pass
            return

        if mode not in OPERATING_MODES:
            raise MachineError('Unexpected mode: {}'.format(mode))

        if self._check_operating_mode(mode, raise_exception=False):
            logging.info('Operating mode {} already active'.format(mode))
            return

        logging.info('Setting operating mode to {}'.format(mode))

        if mode == 'master':
            self.slave_refresh_interval = float(self.config.get(
                'slaves', 'refresh_interval', fallback=0.5))
            self.activate_mode(mode)
        elif mode == 'slave':
            master = kwargs.get('master')
            if master is None:
                raise MachineError('No master supplied')

            if ':' in master:
                master, port = master.split(':')
            else:
                port = None

            self.master = master
            self.master_port = port if port else \
                self.config.get('osc', 'reply_port', fallback=6969)

            self.activate_mode(mode)
        elif mode == 'standalone':
            self.activate_mode(mode)

    def set_ip_address(self, new_ip):
        if '/' not in new_ip:
            new_ip += '/8'

        self.ethernet_interface.add_ip(new_ip)
        self.ethernet_interface.del_ip(self.ip_address)

    def activate_mode(self, mode):
        if mode not in ('standalone', 'master', 'slave'):
            raise MachineError('Unexpected mode: {}'.format(mode))

        if mode == 'standalone':
            self._machine_keys = StandaloneMachineMode(self)
            self.operating_mode = mode
            self['machine:command:timeout_enable'] = False
        elif mode == 'master':
            if not self.slave_machines:
                raise MachineError('No slaves found')

            for s in self.slave_machines.values():
                s.enslave()

            self._machine_keys = MasterMachineMode(self)
            self.operating_mode = mode
            self['machine:command:timeout_enable'] = False

            self.start_slaves_loop()
        elif mode == 'slave':
            if not self.master:
                raise MachineError('No master specified')

            if not self.master_port:
                raise MachineError('No port specified for master')

            self._machine_keys = SlaveMachineMode(self)
            self.operating_mode = mode
            self['machine:command:timeout_enable'] = True

            self._slave_timeout = float(self.config.get('machine', 'timeout_as_slave', fallback=1.5))
            self._timeout_thread = Thread(target=self._timeout_watcher)
            self._timeout_thread.daemon = True
            self._timeout_thread.start()

    def free(self):
        self.master = None
        self.master_port = None

        self['machine:command:enable'] = False

        self.activate_mode('standalone')
        self._running_event.set()


    # Properties
    @property
    def infos(self):
        rev = self.cape_infos['revision'] if self.cape_infos \
            else '0000'
        var = self.config['machine']['variant'].split('.')

        return ('identify', var[0].upper(), var[1].upper(), rev)

    @property
    def serialnumber(self):
        if self.config.get('machine', 'force_serialnumber', fallback=False):
            return self.config.get('machine', 'force_serialnumber')

        if not self.cape_infos:
            return

        sn = self.cape_infos['serialnumber'] if self.cape_infos \
            else '000000000000'

        return sn

    @property
    def osc_address(self):
        try:
            a, m = self.ethernet_interface.ips[-1].split('/')
            p = self.config.getint('osc', 'listen_port')
            return '{addr}/{mask}:{port}'.format(addr=a, mask=m, port=p)
        except (IndexError, KeyError):
            return '0.0.0.0/0:00'

    @property
    def ip_address(self):
        ip, mask = self.ethernet_interface.ips[-1].split('/')
        return ip

    @property
    def cidr_mask(self):
        ip, mask = self.ethernet_interface.ips[-1].split('/')
        return mask

    @property
    def parameters(self):
        p = {}
        p += self._profile_parameters
        if self.frontend:
            p += self.frontend.parameters


    # Privates
    def _switch_cb(self, sw_state):
        if sw_state['function']:
            n, f, h = sw_state['name'], sw_state['function'], sw_state['hit']
            logging.debug('Switch activated: {0}, {1}, {2}'.format(n, f, h))
            if 'drive_enable' == f:
                self['machine:command:enable'] = True if h else False
                self.switch_states[n] = h
                logging.info('Switch: {0} {1} with {2}'.format(
                    f, 'enabled' if h else 'disabled', n))
            elif 'toggle_drive_enable' == f:
                if h:
                    sw_st = self.switch_states.get(n, False)

                    self['machine:command:enable'] = not sw_st
                    self.switch_states[n] = not sw_st
                    logging.info('Switch: {0} toggled ({1}) with {2}'.format(
                        f, 'on' if not sw_st else 'off', n))

    def _slaves_loop(self):
        while not self._slaves_running_event.is_set():
            if not self.slaves_channel:
                logging.error('Missing channel for slaves')

            keys_to_send = []
            for sm in self.slave_machines.values():
                for key in sm.forward_keys:
                    if key not in keys_to_send:
                        keys_to_send.append(key)

            for key in keys_to_send:
                try:
                    v = self[key.source or key.dest]
                    rq = SlaveRequest(key.dest, v,
                                      source=key.source, setitem=True)
                    self.slaves_channel.send(rq)
                except AbstractDriverError:
                    pass
                except AbstractMachineError as e:
                    logging.error(repr(e))

            self._slaves_running_event.wait(self.slave_refresh_interval)

    def _slaves_cb(self, rq):
        pass

    def __getitem__(self, key):
        dst = self._get_destination(key)
        key = key.split(':', maxsplit=1)[1]

        if dst is not self:
            return dst[key]

        if self.slave_mode:
            self._last_command_time = time.time()

        return self.machine_keys[key]

    def __setitem__(self, key, value):
        if isinstance(value, (tuple, list)) and len(value) == 1:
            value, = value

        dst = self._get_destination(key)
        key = key.split(':', maxsplit=1)[1]

        if dst is not self:
            dst[key] = value
            return dst[key]

        if self.slave_mode:
            if self._timeout_event.is_set() and not self['machine:status:drive_enable']:
                self.machine_keys['machine:command:enable'] = True
                self._timeout_event.clear()
            self._last_command_time = time.time()
        elif self.master_mode:
            if 'command:enable' in key:
                for sm in self.slave_machines.values():
                    sm.set_to_remote('machine:command:enable', True if value else False)

        self.machine_keys[key] = value

    def _get_destination(self, key):
        if key.startswith('drive:'):
            return self.driver
        elif key.startswith('machine:'):
            return self

        raise ValueError('Unable to find target %s' % key)

    def getitem(self, key):
        return getattr(self, key)

    def setitem(self, key, value):
        setattr(self, key, value)

    def _timeout_watcher(self):
        self._running_event.clear()
        while not self._running_event.is_set():
            if self['machine:status:drive_enable'] is False:
                self._running_event.wait(self._slave_timeout)
                continue

            if time.time() - self._last_command_time > self._slave_timeout:
                self._timeout_event.set()
                self['machine:command:enable'] = False
                logging.error('Timeout detected, disabling drive')

            self._running_event.wait(self._slave_timeout)
