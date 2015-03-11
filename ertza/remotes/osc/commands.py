# -*- coding: utf-8 -*-

import configparser
import liblo as lo

from ...config import DEFAULT_CONTROL_MODE
from ...errors import TimeoutError, SlaveError
from .server import OSCBaseServer
from .slave.communication import SlaveRequest


class OSCCommands(OSCBaseServer):
    """
    OSCCommands contains all commands available thru OSCServer.
    """
    def __init__(self, *args, **kwargs):
        if 'slave' in kwargs:
            self._slave = kwargs['slave']
            self.slave_request = SlaveRequest(self._slave)
        else:
            self._slave = None

        super(OSCCommands, self).__init__(*args, **kwargs)

    def enable_control_mode(self, ctrl_mode=DEFAULT_CONTROL_MODE):
        super(OSCCommands, self).enable_control_mode(ctrl_mode)

        if ctrl_mode == 'slave':
            self.del_method('/control/', None)
        elif ctrl_mode == 'serial':
            self.del_method('/control/', None)

    def setup_reply(self, sender, *args):
        return self.reply('/setup/return', sender, *args)

    def status_reply(self, sender, *args):
        return self.reply('/status', sender, *args, merge=True)

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

    @lo.make_method('/setup/enslave/to', 's')
    @lo.make_method('/setup/enslave/mode', 's')
    def enslave_callback(self, path, args, types, sender):
        if '/to' in path:
            master, = args
            try:
                self.slave_request.set_master(master)
                r = master
            except (SlaveError) as e:
                r = repr(e)
        elif '/mode' in path:
            mode, = args
            try:
                self.slave_request.set_mode(mode)
                r = mode
            except (SlaveError) as e:
                r = repr(e)

        self.setup_reply(sender, '/'.join(path.split('/')[1:]), r)

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

    @lo.make_method('/request/announce', '')
    def request_announce_callback(self, path, args, types, sender):
        self.lg.debug('Received announce request. Replying.')
        self.announce()

    @lo.make_method(None, None)
    def fallback_callback(self, path, args, types, sender):
        self.setup_reply(sender, "/status/wrong_osc_command", path, types, *args)
