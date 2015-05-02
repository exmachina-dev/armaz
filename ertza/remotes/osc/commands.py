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

    def timeout_reply(self, sender, *args):
        return self.reply('/timeout', sender, *args, merge=False)

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

    @lo.make_method('/setup/get', None)
    def setup_get_callback(self, path, args, types, sender):
        if len(args) != 2:
            self.setup_reply(sender, "One or more argument is missing.")
        setup_section, setup_var = args
        try:
            args.append(self.config_request.get(setup_section, setup_var))
            self.setup_reply(sender, path, *args)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            self.setup_reply(sender, setup_section, str(repr(e)))

    @lo.make_method('/setup/dump', None)
    def setup_get_callback(self, path, args, types, sender):
        section = None
        if len(args) is 1:
            section = args[0]

        try:
            self.lg.debug('Dumping config to %s' % (sender.get_hostname(),))
            dump = self.config_request.dump(section)
            for k, v in dump.items():
                self.setup_reply(sender, '/setup/value', k[0], k[1], v)
            self.setup_reply(sender, '/setup/dump/done')
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            self.setup_reply(sender, section, str(repr(e)))

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

    @lo.make_method('/debug/drive/drive_enable', 'i')
    def debug_drive_enable_callback(self, path, args, types, sender):
        st, = args
        try:
            rtn = self.mdb_request.set_command(drive_enable=st)
            self.status_reply(sender, '/debug/drive/return', rtn)
        except TimeoutError as e:
            self.timeout_reply(sender, path, repr(e))
            pass

    @lo.make_method('/debug/drive/clear_errors', 'i')
    def debug_clear_errors_callback(self, path, args, types, sender):
        st, = args
        print(st)
        try:
            rtn = self.mdb_request.set_command(clear_errors=st)
            self.status_reply(sender, '/debug/drive/return', rtn)
        except TimeoutError as e:
            self.timeout_reply(sender, path, repr(e))
            pass

    @lo.make_method('/debug/drive/speed', 'i')
    def debug_drive_speed_callback(self, path, args, types, sender):
        sp, = args
        try:
            rtn = self.mdb_request.set_speed(sp)
            self.status_reply(sender, '/debug/drive/return', *rtn)
        except TimeoutError as e:
            self.timeout_reply(sender, path, repr(e))
            pass

    @lo.make_method('/motor/status', '')
    def drive_status_callback(self, path, args, types, sender):
        base = 'motor/'
        try:
            status = self.mdb_request.status
            try:
                for k, v in status.items():
                    path = base + k.split('_', maxsplit=1)[1]
                    self.status_reply(sender, path, v)
            except AttributeError:
                self.status_reply(sender, base + 'error',
                        'Unable to get status')

            errcode = self.mdb_request.error_code
            temp = self.mdb_request.drive_temperature

            if not errcode:
                errcode = 'Unable to get error code'
            if not temp:
                temp = 'Unable to get drive temperature'

            self.status_reply(sender, base + 'error_code', errcode)
            self.status_reply(sender, base + 'drive_temperature', temp)
        except TimeoutError as e:
            self.timeout_reply(sender, path, repr(e))
            pass

    @lo.make_method('/request/announce', '')
    def request_announce_callback(self, path, args, types, sender):
        self.lg.debug('Received announce request. Replying.')
        self.announce()

    @lo.make_method(None, None)
    def fallback_callback(self, path, args, types, sender):
        self.lg.debug('Received wrong command. Ignoring.')
        self.setup_reply(sender, "/status/wrong_osc_command", path, types, *args)
