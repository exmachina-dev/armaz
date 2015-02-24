# -*- coding: utf-8 -*-

from ertza.base import BaseResponse, BaseRequest

class ModbusRequest(BaseRequest):
    def _check_args(self, *args):
        self.args = args
        if self.args:
            self.method = None
            self.value = None

    def get_status(self, *args):
        self._check_args(*args)
        self.method = self._methods['get_status']
        rp = self.send()
        return rp.value

    def get_errorcode(self, *args):
        self._check_args(*args)
        self.method = self._methods['get_errorcode']
        rp = self.send()
        return rp.value

    def get_command(self, *args):
        self._check_args(*args)
        self.method = self._methods['get_command']
        rp = self.send()
        return rp.value

    def set_command(self, *args):
        self._check_args(*args)
        self.method = self._methods['set_command']
        return self.send().value

    def dump(self, *args):
        self._check_args(*args)
        self.method = self._methods['dump']
        return self.send().value


class ModbusResponse(BaseResponse):
    def __init__(self, target, request, end=None, *args):
        super(ModbusResponse, self).__init__(target, *args)
        self.request = request
        self._end = end

    def get_from_device(self, *args):
        if not self._end:
            raise ValueError("Modbus isn't defined.")

        if self.request.method & self._methods['get_status']:
            self.method = self._methods['get_status']
            self.value = self._end.get_status()
        elif self.request.method & self._methods['get_command']:
            self.method = self._methods['get_command']
            self.value = self._end.get_command()
        elif self.request.method & self._methods['get_errorcode']:
            self.method = self._methods['get_errorcode']
            self.value = self._end.get_errorcode()

    def set_to_device(self, *args):
        self.method = self._methods['set']

        if not self._end:
            raise ValueError("Modbus isn't defined.")
        if len(args) == 3:
            section, option, value = args
        else:
            raise ValueError("One or more argument is missing.")
        self.value = self._end.set(str(section), str(option), str(value))

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
        if self.request.method & self._methods['set']:
            self.set_to_config(*args)
        elif self.request.method & self._methods['get']:
            self.get_from_device(*args)
        elif self.request.method & self._methods['dump']:
            self.dump_config(*args)
        else:
            raise ValueError('Unexcepted method: %s', self.request.method)

        return self.value
