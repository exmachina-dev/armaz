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
        if self.mode == 'master':
            self.server_port = int(self.config_request.get(
                    'enslave', 'master_port', 7902))
            self.client_port = int(self.config_request.get(
                    'enslave', 'slave_port', 7903))
            self.slaves_datastore = self.config_request.get(
                    'enslave', 'slaves_datastore',
                    '/var/local/ertza/slaves.data')
            self._load_slaves()
        elif self.mode == 'slave':
            self.server_port = int(self.config_request.get(
                    'enslave', 'slave_port', 7903))
            self.client_port = int(self.config_request.get(
                    'enslave', 'master_port', 7902))
            self.master = self.config_request.get(
                    'enslave', 'master')
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

    @lo.make_method('/setup/set', 'ssi')
    @lo.make_method('/setup/set', 'ssh')
    @lo.make_method('/setup/set', 'ssf')
    @lo.make_method('/setup/set', 'ssd')
    @lo.make_method('/setup/set', 'ssc')
    @lo.make_method('/setup/set', 'sss')
    @lo.make_method('/setup/set', 'ssS')
    @lo.make_method('/setup/set', 'ssm')
    @lo.make_method('/setup/set', 'ssT')
    @lo.make_method('/setup/set', 'ssF')
    @lo.make_method('/setup/set', 'ssN')
    @lo.make_method('/setup/set', 'ssI')
    @lo.make_method('/setup/set', 'ssb')
    def setup_set_callback(self, path, args, types, sender):
        setup_sec, setup_opt, args, = args

        try:
            _value = self.config_request.set(setup_sec, setup_opt, str(args))
            self.setup_reply(sender, path, setup_sec, setup_opt, _value)
        except configparser.NoOptionError as e:
            self.setup_reply(sender, path, setup_sec, str(e))
        except configparser.NoSectionError as e:
            self.setup_reply(sender, str(e))

        self.lg.debug('Executed %s %s.%s %s (%s) from %s',
                path, setup_sec, setup_opt, args, types, sender.get_hostname())

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

    @lo.make_method('/setup/save', '')
    def setup_save_callback(self, path, args, types, sender):
        self.config_request.save()


    @lo.make_method('/osc/restart', '')
    def osc_restart_callback(self, path, args, types, sender):
        self.setup_reply(sender, path, "Restarting.")
        self.restart()

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

    def remove_from_slaves(self, slv):
        return self.slaves.pop(slv, False)

    def _load_slaves(self):
        try:
            with open(self.slaves_datastore, 'rb') as f:
                self.slaves = pickle.load(f)
        except FileNotFoundError:
            self.slaves = {}

    def _save_slaves(self):
        with open(self.slaves_datastore, 'wb') as f:
            pickle.dump(self.slaves, f, pickle.HIGHEST_PROTOCOL)
