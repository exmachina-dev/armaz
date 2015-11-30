# -*- coding: utf-8 -*-

from threading import Thread
import time
import logging


class TempWatcher(object):

    callback = None

    def __init__(self, thermistor, fan, name):
        self.thermistor = thermistor
        self.fan = fan
        self.name = name
        self.current_temp = 0.0
        self.target_temp = 0.0
        self.max_temp = 0.0
        self.P = 0.1
        self.I = 0.005
        self.error_integral = 0.0
        self.running_time = 0.0
        self.interval = 1

    def set_target_temperature(self, temp):
        self.target_temp = float(temp)

    def set_max_temperature(self, temp):
        self.max_temp = float(temp)

    @property
    def temperature(self):
        return self.current_temp

    @property
    def target_reached(self):
        if self.tagret_temp == 0:
            return True
        err = abs(self.temperature - self.target_temp)
        return err < self.ok_range

    def enable(self):
        self.enabled = True
        self.disabled = False
        self.t = Thread(target=self.keep_temperature)
        self.t.daemon = True
        self.t.start()

    def disable(self):
        self.enabled = False

        while self.disabled is False:
            time.sleep(0.5)

        self.fan.set_power(0.0)

    def keep_temperature(self):

        while self.enabled:
            self.current_temp = self.thermistor.temperature
            error = self.target_temp - self.current_temp
            error *= -1

            if self.current_temp >= self.max_temp:
                if self.callback:
                    self.callback()
            self.running_time += self.interval
            _P = self.P * error

            self.error_integral += error * self.interval
            # Clamp error_integral to max output power; More reactive I
            self.error_integral = max(min(self.error_integral, 100.0), 00.0)
            _I = self.I * self.error_integral

            power = _P + _I
            power = max(min(power, 1.0), 0.0)

            self.fan.set_value(power)
            logging.debug("Current temp for %s: %d, Fan \
                          %s set to %s | E: %d I: %d" %
                          (self.thermistor.name, self.current_temp,
                           self.fan.channel, power, error, self.error_integral))
            time.sleep(self.interval)
        self.disabled = True
