# -*- coding: utf-8 -*-

from ..config import ConfigRequest
from ..errors import RemoteError
from .modbus import ModbusRequest

try:
    import Adafruit_BBIO.GPIO as GPIO
    import Adafruit_BBIO.ADC as ADC
    import Adafruit_BBIO.PWM as PWM
except ImportError as e:
    pass
 
SWITCH_PINS = ("P8_10", "P8_11",)
TEMP_PINS = ('P9_39', 'P9_40',)
TEMP_TARGET = (35.0, 40.0,) # in °C
FAN_PINS = ('P8_13', 'P8_19',)

class RemoteServer(object):
    def __init__(self, config, **kwargs):
        self.fake_mode = False
        self._modbus, self.restart_event = None, None
        self._config = config

        if 'fake_mode' in kwargs:
            self.fake_mode = kwargs['fake_mode']

        if 'modbus' in kwargs:
            self._modbus = kwargs['modbus']
            self.mdb_request = ModbusRequest(self._modbus)

        if 'logger' in kwargs:
            self.lg = kwargs['logger']
        else:
            import logging
            self.lg = logging.getLogger()

        if 'restart_event' in kwargs:
            self.restart_event = kwargs['restart_event']

        self.config_request = ConfigRequest(self._config)

        try:
            if not self.fake_mode:
                for p in SWITCH_PINS:
                    GPIO.setup(p, GPIO.IN)
                    GPIO.output(p, GPIO.HIGH)
        except RuntimeError as e:
            raise RemoteError(
                    'Error configuring pins, am I on a beaglebone ?',
                    self.lg) from e


        try:
            if TEMP_PINS and not self.fake_mode:
                ADC.setup()
                for s, f, t in zip(TEMP_PINS, FAN_PINS, TEMP_TARGET):
                    self._temp_watcher.append(TempWatcher(s, f, t))
        except RuntimeError as e:
            raise RemoteError(
                    'Error enabling fan pins, am I on a beaglebone ?',
                    self.lg) from e

    def run(self):
        for tw in self._temp_watcher:
            tw.set_pid()

    def __del__(self):
        GPIO.cleanup()

class TempWatcher(object):
    def __init__(self, sensor, fan, target_temp):
        self.sensor = sensor
        self.fan_pin = fan
        self.fan = PWM.start(fan, 0)
        self.target_temp = target_temp

        self.coeff_g = 1
        self.coeff_ti = 0.1
        self.coeff_td = 0.1

    def set_pid(self):
        self.get_error()
        _cmd = self.get_pid()
        self.fan.set_duty_cycle(_cmd)

    def get_error(self):
        self.error_last = self.error
        self.error = self.target - self.get_temp()
        self.error_sum += self.error
        self.error_delta = self.error - self.error_last

    def get_pid(self):
        return self.p() + self.i() + self.d()

    def get_p(self):
        return self.error * self.coeff_g

    def get_i(self):
        return self.error_sum * self.coeff_ti

    def get_d(self):
        return self.coef_td * self.error_delta

    def __del__(self):
        PWM.stop(self.fan_pin)
        PWM.cleanup()
