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
from ..machines import Machine
from ..machines.slave import SlaveMachineError, FatalSlaveMachineError, SlaveRequest
from ..remotes import AbstractRemote, RemoteType, get_remote_class

from ..drivers.utils import retry

from ..configparser import parameter as _p

from .filters import Filter
from .exceptions import MotionError, FatalMotionError


logging = logging.getLogger('ertza.motion')


class MotionUnit(object):
    def __init__(self, *args, **kwargs):
        AbstractRemote.send_message = self.send_message
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
        self.remotes = {}
        self.alive_remotes = {}

        self._last_command_time = time.time()
        self._running_event = Event()
        self._timeout_event = Event()

        self.slave_refresh_interval = 1

        self.switch_callback = self._switch_cb
        self.switch_states = {}

        self.target_filters = list()

    def start(self):
        self.register_filter(alias_mask='/identify', protocol='OSC', exclusive=True, is_reply=True,
                             target=self.update_alive_machines, args_length=2)
        self.register_filter(alias_mask='/identify', protocol='OSC', exclusive=True, is_reply=True,
                             target=self.update_alive_units, args_length=3)
        self.register_filter(alias_mask='/alive', protocol='OSC', exclusive=True,
                             target=self.update_alive_machines, args_length=2)
        self.register_filter(alias_mask='/alive', protocol='OSC', exclusive=True,
                             target=self.update_alive_units, args_length=3)
        self.discover_nodes()

        # Add a serial remote
        self.register_remote(RemoteType.Varmo)

    def stop(self):
        "Stop all machines and motion server"

        self._running_event.set()

        if self.machines:
            for m in self.machines.values():
                m.exit()

    def handle(self, msg, **kwargs):
        """
        Filter a message coming from a processor, apply filters
        and decide what to do
        """

        for f in self.target_filters:
            if f.accepts(msg):
                f.handle(msg)
                logging.debug('%s handled by %s', repr(msg), str(f))
                if f.is_exclusive:
                    return

        # p.execute(m)

    def discover_nodes(self):
        """
        Send a identify request to broadcast.
        """

        self.alive_machines = {}
        self.alive_remotes = {}
        m = OscMessage('/identify', hostname='10.255.255.255')
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

        logging.info('New machine %s found at %s.', sn, ip)

        if sn in self.config.get('motion', 'machine_serialnumber[]', fallback=list()):
            self.register_machine(sn=sn)

    def update_alive_units(self, m):
        if len(m.args) != 3:
            return False
        sn, ip, tp = m.args
        ip, pt = ip.split(':')
        if '/' in ip:
            ip, nm = ip.split('/')
        else:
            nm = None

        unit = {
                'serialnumber': sn,
                'ip_address': ip,
                'port': pt,
                'cidr': nm,
                'type': tp,
            }
        if tp in REMOTE_TYPES:
            self.alive_remotes[(sn, ip,)] = unit
            logging.info('New remote %s found at %s.', sn, ip)
        else:
            self.alive_machines[(sn, ip,)] = unit
            logging.info('New machine %s found at %s.', sn, ip)

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

        if sni is None and ipi is None:
            raise KeyError('Machine not found')

        # Always prefer machines with serialnumber
        if sni is None:
            i = ipi
        else:
            i = sni
        m = self.alive_machines[alive_keys[i]]
        try:
            s = 'machine_' + alive_keys[i][0]
            if self.config.has_section(s):
                m['config'] = self.config[s]
        except Exception as e:
            logging.exception(e)

        asn, aip = alive_keys[i]

        machine = Machine(**m)
        # Redirect all trafic from this machine to its Machine
        self.register_filter(sender=aip, target=machine.handle, exclusive=True)
        self.machines[(asn, aip,)] = machine

        logging.info('Machine %s registered.', str(machine))

        machine.start()

    def register_remote(self, remote_type, sn=None, ip=None):
        asn, aip = None, None

        if sn is not None or ip is not None:
            alive_keys = list(self.alive_remotes.keys())

            sni = None
            ipi = None
            for i, k in enumerate(alive_keys):
                if sn and sn == k[0]:
                    sni = i

                if ip and ip == k[1]:
                    ipi = i

            if sni is None and ipi is None:
                raise KeyError('Machine not found')

            # Always prefer remote with serialnumber
            if sni is None:
                i = ipi
            else:
                i = sni
            m = self.alive_machines[alive_keys[i]]

            asn, aip = alive_keys[i]

        config = {
            'ip': aip,
            'serialnumber': asn,
        }

        remote_class = get_remote_class(remote_type)
        if not remote_class:
            logging.error('No remote for %s', str(remote_type))
            return

        remote = remote_class(**config)
        print(remote.__class__.__name__)
        # Redirect all trafic from this machine to its Machine
        if remote.HAS_IP:
            self.register_filter(sender=aip, target=remote.handle, exclusive=True)
        else:
            self.register_filter(protocol=remote.PROTOCOL, target=remote.handle, exclusive=True)

        self.remotes[remote.uid] = remote

        remote.start()

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
    def osc_port(self):
        try:
            return int(self.config.get('osc', 'listen_port'))
        except TypeError:
            return 0

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
