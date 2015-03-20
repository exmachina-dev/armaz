# -*- coding: utf-8 -*-

try:
    import Adafruit_BBIO.GPIO as GPIO
    import Adafruit_BBIO.ADC as ADC
    import Adafruit_BBIO.PWM as PWM
except ImportError as e:
    TEST_MODE = True
 
SWITCH_PINS = ("P8_10", "P8_11",)
TEMP_PINS = ('P9_39', 'P9_40',)
TEMP_TARGET = (35.0, 40.0,) # in °C
FAN_PINS = ('P8_13', 'P8_19',)

class RemoteServer(object):
    def __init__(self):
        if TEST_MODE:
            return False

        for p in SWITCH_PINS:
            GPIO.setup(p, GPIO.IN)
            GPIO.output(p, GPIO.HIGH)

        if TEMP_PINS:
            ADC.setup()
            for s, f, t in zip(TEMP_PINS, FAN_PINS, TEMP_TARGET):
                self._temp_watcher.append(TempWatcher(s, f, t))

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
