# -*- coding: utf-8 -*-

import configparser
import liblo as lo

from .server import OSCBaseServer
from ...base import BaseResponse, BaseRequest
from ...errors import SlaveError, TimeoutError
from ...utils import timeout


class OSCSlave(OSCBaseServer):
    """
    OSCSlave contains for enslaving registered slaves or act as a slave.
    """
    def __init__(self, config_pipe, logger, restart_event, blockall_event,
            modbus_pipe):
        super(OSCSlave, self).__init__(config_pipe, logger, restart_event,
                no_config=True)
        self.blockall_event = blockall_event
        self.modbus_pipe = modbus_pipe

        self.mode = self.config_request.get(
                'enslave', 'mode', 'master')
        if self.mode == 'master':
            self.server_port = int(self.config_request.get(
                'enslave', 'master_port', 7902))
            self.client_port = int(self.config_request.get(
                'enslave', 'slave_port', 7903))
        elif self.mode == 'slave':
            self.server_port = int(self.config_request.get(
                'enslave', 'slave_port', 7903))
            self.client_port = int(self.config_request.get(
                'enslave', 'master_port', 7902))
        else:
            err = SlaveError('Unexpected mode: %s' % self.mode)
            self.lg.error(err)
            raise err
        self.broadcast_address = self.config_request.get(
            'enslave', 'broadcast', '192.168.1.255')

        self.create_server()

    def announce(self):
        address = lo.Address(self.broadcast_address, self.client_port)
        msg = lo.Message('/enslave/master/online', self.server_port)
        return self.send(address, msg)

    def slave_reply(self, sender, *args):
        return self.reply('/enslave/slave', sender, *args)

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

    @lo.make_method('/enslave/register', '')
    def request_announce_callback(self, path, args, types, sender):
        self.lg.debug('Received slave register from %s', sender)
        self.announce()

    @lo.make_method(None, None)
    def fallback_callback(self, path, args, types, sender):
        self.setup_reply(sender, "/status/wrong_osc_command", path, types, *args)


class SlaveRequest(BaseRequest):
    def get_status(self, *args):
        return self._build_rq('get_status', *args)

    def get_error_code(self, *args):
        return self._build_rq('get_error_code', *args)

    def get_drive_temperature(self, *args):
        return self._build_rq('get_drive_temperature', *args)

    def get_command(self, *args):
        return self._build_rq('get_command', *args)

    def set_command(self, *args):
        self._check_args(*args)
        self.method = self._methods['set_command']
        return self.send().value

    def dump(self, *args):
        self._check_args(*args)
        self.method = self._methods['dump']
        return self.send().value


class SlaveResponse(BaseResponse):
    def __init__(self, target, request, end=None, *args):
        super(ModbusResponse, self).__init__(target, *args)
        self.request = request
        self._end = end

    @timeout(1, "Slave didn't respond.")
    def get_from_device(self, *args):
        if not self._end:
            raise ValueError("Modbus isn't defined.")

        if self.request.method == self._methods['get_status']:
            self.method = self._methods['get_status']
            self.value = self._end.get_status()
        elif self.request.method == self._methods['get_command']:
            self.method = self._methods['get_command']
            self.value = self._end.get_command()
        elif self.request.method == self._methods['get_error_code']:
            self.method = self._methods['get_error_code']
            self.value = self._end.get_error_code()
        elif self.request.method == self._methods['get_drive_temperature']:
            self.method = self._methods['get_drive_temperature']
            self.value = self._end.get_drive_temperature()

    @timeout(1, "Slave didn't respond.")
    def set_to_device(self, *args):
        self.method = self._methods['set']

        if not self._end:
            raise ValueError("Modbus isn't defined.")
        if len(args) == 3:
            section, option, value = args
        else:
            raise ValueError("One or more argument is missing.")
        self.value = self._end.set(str(section), str(option), str(value))

    @timeout(1, "Slave didn't respond.")
    def dump_config(self, *args):
        self.method = self._methods['dump']

        if not self._end:
            raise ValueError("Modbus isn't defined.")
        if len(args) == 1:
            section, = args
        else:
            section = None
        self.value = self._end.dump(str(section))

    def handle(self):
        args = self.request.args
        try:
            if self.request.method & self._methods['set']:
                self.set_to_config(*args)
            elif self.request.method & self._methods['get']:
                self.get_from_device(*args)
            elif self.request.method & self._methods['dump']:
                self.dump_config(*args)
            else:
                raise ValueError('Unexcepted method: %s', self.request.method)

            return self.value
        except TimeoutError as e:
            raise e
        finally:
            return None
