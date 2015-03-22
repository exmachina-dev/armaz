# -*- coding: utf-8 -*-

from ...base import BaseResponse, BaseRequest
from ...errors import TimeoutError, ModbusMasterError
from ...utils import timeout

class ModbusRequest(BaseRequest):
    @property
    def status(self):
        return self._build_rq('get_status')

    @property
    def error_code(self):
        return self._build_rq('get_error_code')

    @property
    def drive_temperature(self):
        return self._build_rq('get_drive_temperature')

    @property
    def command(self):
        return self._build_rq('get_command')

    @property
    def speed(self):
        return self._build_rq('get_speed')

    def get(self, command, *args):
        if command not in self._methods:
            return ValueError('Unexcepted method: %s' % command)
        return self._build_rq(command, *args)

    def set_command(self, *args):
        return self._build_rq('set_command', *args)

    def set_speed(self, *args):
        return self._build_rq('set_speed', *args)

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

        mth = self.methods
        opts = {
                mth['get_status']: self._end.get_status,
                mth['get_command']: self._end.get_command,
                mth['get_error_code']: self._end.get_error_code,
                mth['get_speed']: self._end.get_speed,
                mth['get_encoder_velocity']: self._end.get_encoder_velocity,
                mth['get_encoder_position']: self._end.get_encoder_position,
                mth['get_drive_temperature']: self._end.get_drive_temperature,
                mth['get_dropped_frames']: self._end.get_dropped_frames,
                }

        try:
            self.method = self.request_method
            self.value = opts[self.request_method]()
        except IndexError:
            self.value = None
            raise ModbusMasterError('Unexepected method')

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
