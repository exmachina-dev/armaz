# -*- coding: utf-8 -*-

import os
import configparser
import liblo as lo
import pickle

from ....config import DEFAULT_CONTROL_MODE
from ....errors import SlaveError, TimeoutError
from ..server import OSCBaseServer


class SlaveServer(OSCBaseServer):
    """
    SlaveServer contains for enslaving registered slaves or act as a slave.
    """
    def __init__(self, config_pipe, lg, restart_event, blockall_event,
            modbus_pipe):
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

    def enable_control_mode(self, ctrl_mode=DEFAULT_CONTROL_MODE):
        super(SlaveServer, self).enable_control_mode(ctrl_mode)

        if ctrl_mode == 'osc':
            self.del_method('/control/', None)
        elif ctrl_mode == 'serial':
            self.del_method('/control/', None)

    def run(self, timeout=None):
        super(SlaveServer, self).run(timeout)

    def announce(self):
        address = lo.Address(self.broadcast_address, self.client_port)
        msg = lo.Message('/enslave/' + self.mode + '/online', self.server_port)
        return self.send(address, msg)

    def slave_reply(self, sender, *args, **kwargs):
        return self.reply('/enslave/slave', sender, *args, **kwargs)

    @lo.make_method('/enslave/get_status', '')
    @lo.make_method('/enslave/get_command', '')
    @lo.make_method('/enslave/get_error_code', '')
    @lo.make_method('/enslave/get_drive_temperature', '')
    def enslave_get_callback(self, path, args, types, sender):
        try:
            _value = self.mdb_request.get(path.split('/')[-1])
            self.slave_reply(sender, path, _value)
        except ValueError as e:
            self.slave_reply(sender, str(e))

        self.lg.debug('Executed %s (%s) from %s',
                path, args, types, sender.get_hostname())

    @lo.make_method('/setup/get', 'ss')
    @lo.make_method('/setup/get', 's')
    @lo.make_method('/setup/get', '')
    def setup_get_callback(self, path, args, types, sender):
        if len(args) != 2:
            self.setup_reply(sender, "One or more argument is missing.")
        setup_section, setup_var = args
        try:
            args.append(self.config_request.get(setup_section, setup_var))
            self.setup_reply(sender, path, *args)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            self.setup_reply(sender, setup_section, str(repr(e)))

    @lo.make_method('/enslave/config/', None)
    def enslave_config_callback(self, path, args, types, sender):
        if len(args) < 3:
            self.slave_reply(sender, 'config', 'Invalid number of arguments')
            return None
        elif len(args) > 3:
            args = (args[0], args[1], args[2:])
        if sender not in self.slaves.keys():
            self.slave_reply(sender, 'config', 'Non-registered slave')
            return None

        sec, opt, value = args
        slave_config = self.slaves[sender]
        slave_config.update({(sec, opt): value,})

    @lo.make_method('/enslave/unregister', '')
    @lo.make_method('/enslave/register', '')
    def slave_register_callback(self, path, args, types, sender):
        sender_host = sender.get_hostname()
        if '/register' in path:
            self.lg.debug('Received slave register from %s', sender_host)
            if sender_host != '127.0.0.1':
                if self.add_to_slaves(sender):
                    self.slave_reply(sender, '/registered', merge=True)
                    self.request_slave_config(sender)
                else:
                    self.slave_reply(sender, '/unable_to_registered',
                            merge=True)
            else:
                self.slave_reply(sender, '/wrong_slave', sender_host,
                        merge=True)
                self.lg.info('Wrong slave adress: %s', sender_host)
        else:
            self.lg.debug('Received slave unregister from %s', sender_host)
            if self.remove_from_slaves(sender):
                self.slave_reply(sender, '/unregistered', merge=True)

    @lo.make_method(None, None)
    def fallback_callback(self, path, args, types, sender):
        self.slave_reply(sender, "/enslave/unknow_command", path, types, *args)

    def request_slave_config(self, slave):
        self.reply('/enslave/dump_config', slave)

    def add_to_slaves(self, slv):
        self.slaves.update({slv: {},})
        self._save_slaves()

    def remove_from_slaves(self, slv):
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
