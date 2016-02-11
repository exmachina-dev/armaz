# -*- coding: utf-8 -*-

import sys
import time
import logging

from threading import Event, Thread

from ertza.machine.AbstractMachine import AbstractMachine
from ertza.machine.AbstractMachine import AbstractMachineError
from ertza.machine.MachineModes import StandaloneMachineMode
from ertza.machine.MachineModes import MasterMachineMode
from ertza.machine.MachineModes import SlaveMachineMode

from ertza.drivers.Drivers import Driver
from ertza.drivers.AbstractDriver import AbstractDriverError

from ertza.machine.Slave import Slave, SlaveMachine
from ertza.machine.Slave import SlaveMachineError, SlaveRequest

from ertza.drivers.Utils import retry

logging = logging.getLogger(__name__)


class MachineError(AbstractMachineError):
    pass


class Machine(AbstractMachine):
    def __init__(self):

        SlaveMachine.machine = self

        self.version = None

        self.config = None
        self.driver = None
        self.cape_infos = None
        self.ip_address = None

        self.comms = {}
        self.processors = {}
        self.commands = None
        self.synced_commands = None
        self.unbuffered_commands = None

        self.slaves = []
        self.master = None
        self.operation_mode = None
        self.machine_keys = None

        self._slave_timeout = 1.0
        self._last_command_time = time.time()

        self.switch_callback = self._switch_cb
        self.switch_states = {}

    def init_driver(self):
        drv = self.config.get('machine', 'driver', fallback=None)
        logging.info("Loading %s driver" % drv)
        if drv is not None:
            try:
                driver_config = self.config['driver_' + drv]
            except KeyError:
                driver_config = {}
                logging.error("Unable to get config for %s driver" % drv)

            try:
                self.driver = Driver().get_driver(drv)(driver_config)
            except KeyError:
                logging.error("Unable to get %s driver, exiting." % drv)
                sys.exit()
        else:
            logging.error("Machine driver is not defined, aborting.")
            return False

        logging.debug("%s driver loaded" % drv)

        self.frontend_config = self.config['motor']
        self.driver.load_frontend_config(self.frontend_config)
        return drv

    def start(self):
        self.driver.connect()

        self.driver.send_default_values()

    def exit(self):
        self.driver.exit()

        if self.master_mode:
            for s in self.slaves:
                s.exit()

        for n, c in self.comms.items():
            c.exit()

    def load_startup_mode(self):
        m = self.config.get('machine', 'operating_mode', fallback='standalone')
        logging.info('Loading {} operating mode'.format(m))

        if m == 'master':
            self.load_slaves()
        if m == 'slave':
            master = self.config.get('machine', 'master')
            self.set_operation_mode(m, master)
        else:
            self.set_operation_mode(m)

    def reply(self, command):
        if command.answer is not None:
            self.send_message(command.protocol, command.answer)

    def send_message(self, msg):
        self.comms[msg.protocol].send_message(msg)

    @property
    def infos(self):
        rev = self.cape_infos['revision'] if self.cape_infos \
            else '0000'
        var = self.config.variant.split('.')

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
    def address(self):
        a = self.ip_address
        p = self.config.getint('osc', 'listen_port')
        return '{addr}:{port}'.format(addr=a, port=p)

    def search_slaves(self):
        slaves_cf = self.config['slaves']
        slaves = []

        for key, item in slaves_cf.items():
            if key.startswith('slave_serialnumber_'):
                slave_id = int(key.split('_')[2])
                slave_sn = item
                slave_ip = slaves_cf['slave_address_%d' % slave_id]
                slave_md = slaves_cf['slave_mode_%d' % slave_id]
                slave_dv = slaves_cf.get('slave_driver_%d' % slave_id,
                                         fallback='Osc').title()

                slave_cf = {}
                if self.config.has_section('slave_%s' % slave_sn):
                    slave_cf = self.config['slave_%s' % slave_sn]

                s = Slave(slave_sn, slave_ip, slave_dv, slave_md, slave_cf)
                logging.info('Found {2} slave at {1} '
                             'with S/N {0}'.format(*s))
                slaves.append(s)

        if not slaves:
            return False

        self.slaves = []
        for s in slaves:
            m = SlaveMachine(s)
            self.slaves.append(m)

        self.slaves = tuple(self.slaves)
        return self.slaves

    @retry(SlaveMachineError, 5, 5, 2)
    def slave_block_ping(self, slave):
        p = slave.ping()
        if isinstance(p, SlaveRequest):
            raise SlaveMachineError('Unable to ping slave {!r} !'.format(slave))

        if isinstance(p, float):
            return p
        else:
            raise MachineError('Unexpected result while pinging {!s}'.format(slave))


    @retry(MachineError, 5, 5, 2)
    def load_slaves(self):
        if not self.slaves:
            if not self.search_slaves():
                logging.info('No slaves found')
                return

        for s in self.slaves:
            logging.debug('Initializing {2} slave at {1} ({0})'.format(*s.slave))
            self.init_slave(s)
            try:
                ping_time = self.slave_block_ping(s)

                logging.info('Slave at {2} took {0:.2} ms to respond'.format(
                    ping_time, *s.slave))
            except AbstractMachineError as e:
                logging.error('Unable to contact {3} slave at {2} ({1}) '
                              '{0}'.format(str(e), *s.slave))
                return

            sn = s.get_from_remote('machine:serialnumber', block=True)
            if type(sn) == str and s.serialnumber != sn:
                infos = s.slave + (s.get_serialnumber(),)
                logging.warn(MachineError('S/N don\'t match for {2} slave '
                                          'at {1} ({0} vs {4})'
                                          ''.format(*infos)))

    def add_slave(self, driver, address, mode, conf={}):
        self._check_operation_mode()

        try:
            s = Slave(None, address, driver.title(), mode, conf)
            sm = SlaveMachine(s)
            self.init_slave(sm)
            sm.ping()
            sm.set_master(self.serialnumber, self.address(driver))

            existing_s = self.get_slave(serialnumber=sm.serialnumber)
            if existing_s:
                raise MachineError('Already existing {2} at {1} '
                                   'with S/N {0}'.format(*existing_s.slave))

            self.slaves.append(sm)
            s = sm.slave
            logging.info('New {2} slave at {1} '
                         'with S/N {0}'.format(*s))
            return s
        except Exception as e:
            raise MachineError('Unable to add slave: %s' % repr(e))

    def remove_slave(self, sn):
        self._check_operation_mode()

        try:
            rm_slave = self.get_slave(sn)
            if not rm_slave:
                raise MachineError('Slave with S/N %s not found' % sn)

            slave_id, slave = rm_slave

            slave.unslave()
            slave.exit()
            slave_instance = self.slaves.pop(slave_id)
            del slave_instance
        except Exception as e:
            raise MachineError('Unable to remove slave: %s' % str(e))

    def get_slave(self, serialnumber=None, address=None):
        if serialnumber:
            for i, s in enumerate(self.slaves):
                if serialnumber == s.slave.serialnumber:
                    return i, s
            logging.error('Unable to find slave by S/N {}'.format(serialnumber))
        elif address:
            for i, s in enumerate(self.slaves):
                if address == s.slave.address:
                    return i, s
            logging.error('Unable to find slave by address {}'.format(address))

        return None, None

    def init_slave(self, slave_machine):
        try:
            slave_machine.init_driver()
            slave_machine.start()
        except SlaveMachineError as e:
            raise MachineError('Couldn\'t initialize {2} slave at {1} '
                               'with S/N {0}: {exc}'.format(*slave_machine.slave,
                                                            exc=e))

    def set_operation_mode(self, *args):
        if len(args) >= 1:
            mode = args[0]
            logging.info('Setting operating mode to {}'.format(mode))

            if mode == 'master':
                if self.master_mode:
                    logging.info('Operating mode {} already active'.format(mode))
                    return

                self.activate_mode(mode)
            elif mode == 'slave':
                if self.slave_mode:
                    raise MachineError('Operating mode {0} already active. '
                                       'You must disable {0} mode before '
                                       'reactiving it'.format(mode))
                if len(args) >= 2:
                    master = args[1]
                else:
                    raise MachineError('No master supplied')

                if ':' in master:
                    master, port = master.split(':')
                else:
                    port = None

                self.master = master
                self.master_port = port if port else \
                    self.config.get('driver_Osc', 'port', fallback=6969)

                self.activate_mode(mode)
            elif mode == 'standalone':
                if self.standalone_mode:
                    logging.info('Operating mode {} already active'.format(mode))
                    return

                self.activate_mode(mode)
        else:
            logging.info('Deactivating %s mode' % self.operation_mode)

            if self.operation_mode == 'slave':
                self.free()
                self.master = None

            elif self.operation_mode == 'master':
                pass

    def activate_mode(self, mode):
        if mode not in ('standalone', 'master', 'slave'):
            raise MachineError('Unexpected mode: {}'.format(mode))

        if mode == 'standalone':
            self.machine_keys = StandaloneMachineMode(self)
            self.operation_mode = mode
        elif mode == 'master':
            if not self.slaves:
                raise MachineError('No slaves found')

            for s in self.slaves:
                s.enslave()

            self.machine_keys = MasterMachineMode(self)
            self.operation_mode = mode
        elif mode == 'slave':
            if not self.master:
                raise MachineError('No master specified')

            if not self.master_port:
                raise MachineError('No port specified for master')

            self.machine_keys = SlaveMachineMode(self)
            self.operation_mode = mode

            self._timeout_thread = Thread(target=self._timeout_watcher)
            self._timeout_thread.daemon = True
            self._timeout_thread.start()

    @property
    def slave_mode(self):
        return self._check_operation_mode('slave', raise_exception=False)

    @property
    def master_mode(self):
        return self._check_operation_mode('master', raise_exception=False)

    @property
    def standalone_mode(self):
        return self._check_operation_mode('standalone', raise_exception=False)

    def _check_operation_mode(self, mode='slave', raise_exception=True):
        if self.operation_mode == mode:
            return True

        if raise_exception:
            raise MachineError('Slave mode %s isn\'t activated: %s' % (
                mode, self.operation_mode))
        return False

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
            self._last_command_time = time.time()

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
        _running_event = Event()
        while not _running_event.is_set():
            if time.time() - self._last_command_time > self._slave_timeout:
                self['machine:command:enable'] = False
                logging.error('Timeout detected, disabling drive')

            _running_event.wait(self._slave_timeout)
