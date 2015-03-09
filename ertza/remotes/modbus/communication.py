# -*- coding: utf-8 -*-

from ...base import BaseResponse, BaseRequest
from ...errors import TimeoutError
from ...utils import timeout

class ModbusRequest(BaseRequest):
    def get_status(self, *args):
        return self._build_rq('get_status', *args)

    def get_error_code(self, *args):
        return self._build_rq('get_error_code', *args)

    def get_drive_temperature(self, *args):
        return self._build_rq('get_drive_temperature', *args)

    def get_command(self, *args):
        return self._build_rq('get_command', *args)

    def get(self, command, *args):
        if command not in self._methods:
            return ValueError('Unexcepted method: %s' % command)
        return self._build_rq(command, *args)

    def set_command(self, *args):
        return self._build_rq('set_command', *args)

    def dump(self, *args):
        return self._build_rq('dmp', *args)


class ModbusResponse(BaseResponse):
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
        self.method = self._methods['dmp']

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
            elif self.request.method & self._methods['dmp']:
                self.dump_config(*args)
            else:
                raise ValueError('Unexcepted method: %s' % self.request.method)

            return self.value
        except TimeoutError as e:
            raise e
        finally:
            return None
