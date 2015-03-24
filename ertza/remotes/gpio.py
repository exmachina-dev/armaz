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
            self.run(init=True)
        except RemoteError:
            self.fake_mode = True
            self.run(init=True)

    def run(self, interval=None, init=False):
        if (self.restart_event and self.restart_event.is_set()) or init:
            if not init:
                self.lg.info('Updating remote server…')
            try:
                self.create_switch_pins()
                self.create_temp_watchers()
                if self.restart_event:
                    self.restart_event.clear()
            except RuntimeError as e:
                raise RemoteError(
                        'Error configuring pins, am I on a beaglebone ?',
                        self.lg) from e
                if not self.fake_mode:
                    self.lg.warn('Starting failed. Fallback to fake mode.')
                    self.fake_mode = True
                    self.run()

        if not self.fake_mode:
            self.update_pid()
            self.detect_gpio_state()

    def create_switch_pins(self):
        if not self.fake_mode:
            sw = list()
            for i, p in enumerate(SWITCH_PINS):
                a = self.config_request.get('switch'+str(i), 'action', None)
                r = self.config_request.get('switch'+str(i), 'reverse', False)
                sw.append(SwitchHandler(i, p, a, r))
            self.switchs = tuple(sw)
            return True
        return False

    def create_temp_watchers(self):
        if TEMP_PINS and not self.fake_mode:
            ADC.setup()
            tw = list()
            for s, f, t in zip(TEMP_PINS, FAN_PINS, TEMP_TARGET):
                tw.append(TempWatcher(s, f, t))
            self.temp_watchers = tuple(tw)
            return True
        return False

    def update_pid(self):
        for tw in self.temp_watchers:
            tw.set_pid()

    def detect_gpio_state(self):
        for p in self.switch_pins:
            p.update_state()


    def __del__(self):
        GPIO.cleanup()

class SwitchHandler(object):
    def __init__(self, index, pin, action=None, reverse=False):
        self.index = index
        self.pin = pin
        self.action = action
        self.reverse = reverse

        self.setup_pin()

    def setup_pin(self):
        GPIO.setup(self.pin, GPIO.IN)
        GPIO.output(self.pin, GPIO.HIGH)
        GPIO.add_event_detect(self.pin, GPIO.BOTH)

    def update_state(self):
        if GPIO.event_detected(self.pin):
            self.state = GPIO.input(self.pin)
            return True
        return None


class TempWatcher(object):
    def __init__(self, sensor, fan, target_temp):
        self.sensor = sensor
        self.beta = 3977
        self.map_table = (
                (0, 423),
                (25, 900),
                (40, 1174),
                (55, 1386),
                (70, 1532),
                (85, 1599),
                (100, 1686))
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

    def get_temperature(self):
        raw = ADC.read_raw(self.sensor)
        return raw

    def get_error(self):
        self.error_last = self.error
        self.error = self.target - self.get_temperature()
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
