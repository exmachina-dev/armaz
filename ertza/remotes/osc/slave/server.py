# -*- coding: utf-8 -*-

import configparser
import liblo as lo
import pickle

from ..server import OSCBaseServer
from ....errors import SlaveError, TimeoutError


class SlaveServer(OSCBaseServer):
    """
    SlaveServer contains for enslaving registered slaves or act as a slave.
    """
    def __init__(self, config_pipe, logger, restart_event, blockall_event,
            modbus_pipe):
        super(SlaveServer, self).__init__(config_pipe, logger, restart_event,
                modbus=modbus_pipe, no_config=True)
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

        if not self.mode == 'standalone':
            self.create_server()

    def announce(self):
        address = lo.Address(self.broadcast_address, self.client_port)
        msg = lo.Message('/enslave/master/online', self.server_port)
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

    @lo.make_method('/motor/status', '')
    def drive_status_callback(self, path, args, types, sender):
        base = 'motor/'
        try:
            status = self.mdb_request.get_status()
            try:
                for k, v in status.items():
                    path = base + k.split('_', maxsplit=1)[1]
                    self.status_reply(sender, path, v)
            except AttributeError:
                self.status_reply(sender, base + 'error',
                        'Unable to get status')

            errcode = self.mdb_request.get_error_code()
            temp = self.mdb_request.get_drive_temperature()
            self.lg.debug(errcode)
            self.status_reply(sender, base + 'error_code', errcode)
            self.status_reply(sender, base + 'drive_temperature', temp)
        except TimeoutError as e:
            self.status_reply(sender, base + 'timeout', repr(e))
            pass

    @lo.make_method('/enslave/unregister', '')
    @lo.make_method('/enslave/register', '')
    def slave_register_callback(self, path, args, types, sender):
        if '/register' in path:
            self.lg.debug('Received slave register from %s', sender)
            if self.add_to_bank(sender):
                self.slave_reply(sender, '/registered', merge=True)
        else:
            self.lg.debug('Received slave unregister from %s', sender)
            if self.remove_from_bank(sender):
                self.slave_reply(sender, '/unregistered', merge=True)

    @lo.make_method(None, None)
    def fallback_callback(self, path, args, types, sender):
        self.slave_reply(sender, "/enslave/unknow_command", path, types, *args)

    def add_to_slaves(self, slv):
        self.slaves.update((slv, True))
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
        with open(self.slaves_datastore, 'wb') as f:
            pickle.dump(self.slaves, f, pickle.HIGHEST_PROTOCOL)
