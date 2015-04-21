# -*- coding: utf-8 -*-

import os
import configparser
import liblo as lo
import pickle

from ....config import DEFAULT_CONTROL_MODE
from ....errors import SlaveError, TimeoutError
from ..server import OSCBaseServer

STATES = {
        'EMPTY':        0x00,
        'UPTODATE':     0x01,
        'CHANGED':      0x02,
        'WAITING':      0x03,
        }


class SlaveServer(OSCBaseServer):
    """
    SlaveServer contains commands for enslaving registered slaves or act as a slave.
    """
    def __init__(self, config_pipe, lg, restart_event, blockall_event,
            modbus_pipe, **kwargs):
        super(SlaveServer, self).__init__(config_pipe, logger=lg,
                restart_event=restart_event, modbus=modbus_pipe,
                no_config=True)
        self.blockall_event = blockall_event

        self.mode = self.config_request.get(
                'enslave', 'mode', 'master')
        if self.mode == 'master' or self.mode == 'slave':
            self.server_port = int(self.config_request.get(
                    'enslave', 'master_port', 7902))
            self.client_port = int(self.config_request.get(
                    'enslave', 'slave_port', 7903))

        if 'reverse_ports' in kwargs:
            if kwargs['reverse_ports']:
                self.lg.warn('Reversing server and client ports.')
                self.client_port, self.server_port = self.server_port, self.client_port

        if self.mode == 'master':
            self.slaves_datastore = self.config_request.get(
                    'enslave', 'slaves_datastore')
            self._load_slaves()
        elif self.mode == 'slave':
            self.master = self.config_request.get(
                    'enslave', 'master', None)
        elif self.mode == 'standalone':
            pass
        else:
            err = SlaveError('Unexpected mode: %s' % self.mode)
            self.lg.error(err)
            raise err
        self.broadcast_address = self.config_request.get(
            'enslave', 'broadcast', '192.168.1.255')

        self.control_mode = self.config_request.get(
                'control', 'mode')
        self.enable_control_mode(self.control_mode)

        if not self.mode == 'standalone':
            self.create_server()

        self.start_mode()

    def start_mode(self):
        if self.mode == 'master':
            for slv in self.slaves.keys():
                self.request_slave_config(slv)
        elif self.mode == 'slave':
            self.register_to_master()

    def enable_control_mode(self, ctrl_mode=DEFAULT_CONTROL_MODE):
        super(SlaveServer, self).enable_control_mode(ctrl_mode)

        if ctrl_mode == 'osc':
            self.del_method('/control/', None)
        elif ctrl_mode == 'serial':
            self.del_method('/control/', None)
        elif ctrl_mode == 'slave':
            self.config_request.set('enslave', 'mode', 'slave')

    def run(self, timeout=None):
        super(SlaveServer, self).run(timeout)

    def announce(self, **kwargs):
        """ Send an announce on broadcast address. """

        if 'target' in kwargs.keys():
            address = lo.Address(kwargs['target'], self.client_port)
        else:
            address = lo.Address(self.broadcast_address, self.client_port)
        msg = lo.Message('/enslave/' + self.mode + '/online', self.server_port)
        return self.send(address, msg)

    def slave_reply(self, sender, *args, **kwargs):
        """ Reply from a slave. """
        return self.reply('/enslave/slave', sender, *args, **kwargs)

    def master_reply(self, sender, *args, **kwargs):
        """ Reply from a master. """
        return self.reply('/enslave/master', sender, *args, merge=True,
                **kwargs)

    @lo.make_method('/enslave/get_status', '')
    @lo.make_method('/enslave/get_command', '')
    @lo.make_method('/enslave/get_error_code', '')
    @lo.make_method('/enslave/get_drive_temperature', '')
    def enslave_get_callback(self, path, args, types, sender):
        """ Send slave status. """

        try:
            _value = self.mdb_request.get(path.split('/')[-1])
            self.slave_reply(sender, path, _value)
        except ValueError as e:
            self.slave_reply(sender, str(e))

        self.lg.debug('Executed %s (%s) from %s',
                path, args, types, sender.get_hostname())

    @lo.make_method('/enslave/config/get', None)
    def enslave_config_get_callback(self, path, args, types, sender):
        """ Return config value. """
        if len(args) != 2:
            self.slave_reply(sender, 'config', 'Invalid number of arguments')
        setup_section, setup_var = args
        try:
            args.append(self.config_request.get(setup_section, setup_var))
            self.slave_reply(sender, path, *args)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            self.slave_reply(sender, setup_section, str(repr(e)))

    @lo.make_method('/enslave/config/set', None)
    def enslave_config_set_callback(self, path, args, types, sender):
        """ Update config only if is send be master. """

        if len(args) < 3:
            self.slave_reply(sender, 'config', 'Invalid number of arguments')
            return None
        elif len(args) > 3:
            args = (args[0], args[1], args[2:])

        try:
            slave = self.get_slave(sender)

            sec, opt, value = args
            slave_config = self.slaves[sender]
            slave_config.update({(sec, opt): value,})
        except SlaveError:
            self.slave_reply(sender, 'config', 'Non-registered slave')
            return None


    @lo.make_method('/enslave/config/dump', None)
    def enslave_config_dump(self, path, args, types, sender):
        """ Dump config. """
        self.lg.debug('Dumping config to %s', sender.get_hostname())
        for a, v in self.config_request.dump():
            s, o = a
            self.slave_reply(sender, 'config/value', s, o, v)
        self.slave_reply(sender, 'config/dump_done')

    @lo.make_method('/enslave/slave/unregister', '')
    @lo.make_method('/enslave/slave/register', '')
    def slave_register_callback(self, path, args, types, sender):
        """
        Handle register/unregister request:

        register: Update slaves datastore and request config from slaves.
        unregister: Delete slave from datastore.
        """

        sender_host = sender.get_hostname()
        if '/register' in path:
            self.lg.debug('Received slave register from %s', sender_host)
            if sender_host != '127.0.0.1':
                if self.add_to_slaves(sender):
                    self.master_reply(sender, 'registered')
                    self.request_slave_config(sender)
                else:
                    self.master_reply(sender, 'unable_to_registered')
            else:
                self.master_reply(sender, 'wrong_slave', sender_host)
                self.lg.info('Wrong slave adress: %s', sender_host)
        else:
            self.lg.debug('Received slave unregister from %s', sender_host)
            if self.remove_from_slaves(sender):
                self.master_reply(sender, 'unregistered')

    # Auto-register when master come up
    @lo.make_method('/enslave/master/online', 'i')
    def auto_register_to_master(self, path, args, types, sender):
        """ Auto register if a master is brought online. """

        port, = args
        if sender.get_hostname() == self.master and port == self.server_port:
            self.register_to_master()

    # Auto-annouce to slave when it come up (so it can auto-register)
    @lo.make_method('/enslave/slave/online', 'i')
    def auto_announce_to_slave(self, path, args, types, sender):
        """ If a slave is received, announce to that slave. """
        port, = args
        if sender in self.slaves.keys():
            self.announce(target=sender.get_hostname())

    # Update config state for slave
    @lo.make_method('/enslave/config/dump_done', '')
    def auto_announce_to_slave(self, path, args, types, sender):
        """
        Update config status in  slaves datastore.

        This is received when a slave dump its config.
        """
        slave = self.get_slave(sender)
        slave['config_state'] = STATES['UPTODATE']

    @lo.make_method(None, None)
    def fallback_callback(self, path, args, types, sender):
        """ Default fallback when an unknown command is received. """

        self.slave_reply(sender, "/enslave/unknow_command", path, types, *args)

    def register_to_master(self):
        """
        Register to master

        If no master, return False.
        """
        if self.master:
            return self.slave_reply(lo.Address(self.master, self.server_port), 'register')
        self.lg.info('No master specified, waiting for it.')
        return False

    def request_slave_config(self, slave):
        """ Request config of slave. """
        slave = self.get_slave(slave)
        self.master_reply(slave, 'config/dump')
        self.slaves[slave]['config_state'] = STATES['WAITING']

    def get_slave(self, slave):
        """ Return a slave dict with its config or raise SlaveError if slave
        doesn't exist.
        """

        if slave in self.slaves.keys():
            return slave
        else:
            raise SlaveError('Unregistered slave: %s' % slave.get_hostname(),
                    self.lg)

    def add_to_slaves(self, slv):
        """ Add slave to datastore. """

        self.slaves.update({slv: {},})
        self._save_slaves()

    def remove_from_slaves(self, slv):
        """ Remove slave from datastore. """

        r = self.slaves.pop(slv, False)
        if r:
            self._save_slaves()
        return r

    def _load_slaves(self):
        try:
            with open(self.slaves_datastore, 'rb') as f:
                self.slaves = pickle.load(f)
        except FileNotFoundError:
            self.slaves = {}

    def _save_slaves(self):
        if not os.path.exists(self.slaves_datastore):
            open(self.slaves_datastore, 'a').close()
        with open(self.slaves_datastore, 'wb') as f:
            pickle.dump(self.slaves, f, pickle.HIGHEST_PROTOCOL)
