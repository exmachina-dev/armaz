# -*- coding: utf-8 -*-

from ...base import BaseResponse, BaseRequest
from ...errors import TimeoutError, ModbusMasterError
from ...utils import timeout

class ModbusRequest(BaseRequest):
    def __init__(self, target, slave=None, *args, **kwargs):
        super(ModbusRequest, self).__init__(target, *args, **kwargs)
        self.slave = slave

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

    @property
    def direction(self):
        return self._build_rq('get_direction')

    def get(self, command, *args):
        if command not in self._methods:
            return ValueError('Unexcepted method: %s' % command)
        return self._build_rq(command, *args)

    def set_command(self, *args, **kwargs):
        return self._build_rq('set_command', *args, **kwargs)

    def set_speed(self, *args):
        return self._build_rq('set_speed', *args)

    def set_direction(self, *args):
        return self._build_rq('set_direction', *args)

    def set_acceleration(self, *args):
        return self._build_rq('set_acceleration', *args)

    def set_decelaration(self, *args):
        return self._build_rq('set_deceleration', *args)

    def dump(self, *args):
        return self._build_rq('dmp', *args)


class ModbusResponse(BaseResponse):
    end = None

    def __init__(self, target=None, request=None, *args, **kwargs):
        super(ModbusResponse, self).__init__(target, *args, **kwargs)
        self.request = request
        self._end = self.end

    @timeout(1, "Slave didn't respond.")
    def get_from_device(self, *args):
        if not self._end:
            raise ValueError("Modbus isn't defined.")

        mth = self._methods
        g_opts = {
                mth['get_status']: self._end.get_status,
                mth['get_command']: self._end.get_command,
                mth['get_error_code']: self._end.get_error_code,
                mth['get_speed']: self._end.get_speed,
                mth['get_direction']: self._end.get_direction,
                mth['get_acceleration']: self._end.get_acceleration,
                mth['get_deceleration']: self._end.get_deceleration,
                mth['get_encoder_velocity']: self._end.get_encoder_velocity,
                mth['get_encoder_position']: self._end.get_encoder_position,
                mth['get_drive_temperature']: self._end.get_drive_temperature,
                mth['get_dropped_frames']: self._end.get_dropped_frames,
                }

        try:
            self.method = self.request.method
            self.value = g_opts[self.request.method](*args)
        except IndexError:
            self.value = None
            raise ModbusMasterError('Unexepected method')

    @timeout(1, "Slave didn't respond.")
    def set_to_device(self, *args, **kwargs):
        if not self._end:
            raise ValueError("Modbus isn't defined.")

        mth = self._methods
        s_opts = {
                mth['set_command']: self._end.set_command,
                mth['set_speed']: self._end.set_speed,
                mth['set_direction']: self._end.set_direction,
                mth['set_acceleration']: self._end.set_acceleration,
                mth['set_deceleration']: self._end.set_deceleration,
                }

        try:
            self.method = self.request.method
            self.value = s_opts[self.request.method](*args, **kwargs)
        except IndexError:
            self.value = None
            raise ModbusMasterError('Unexepected method')

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
        kwargs = self.request.kwargs
        try:
            if self.request.method & self._methods['set']:
                self.set_to_device(*args, **kwargs)
            elif self.request.method & self._methods['get']:
                self.get_from_device(*args, **kwargs)
            elif self.request.method & self._methods['dmp']:
                self.dump_config(*args, **kwargs)
            else:
                raise ValueError('Unexcepted method: %s' % self.request.method)

            return self.value
        except TimeoutError as e:
            raise e
        finally:
            return None
