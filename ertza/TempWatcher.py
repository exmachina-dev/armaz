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
        self.P = 1.0
        self.ok_range = 4.0

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

        while self.disabled == False:
            time.sleep(0.5)

        self.fan.set_power(0.0)

    def keep_temperature(self):

        while self.enabled:
            self.current_temp = self.thermistor.temperature
            error = self.target_temp - self.current_temp

            if self.current_temp >= self.max_temp:
                power = 1.0
                if self.callback:
                    self.callback()
            else:
                power = self.P * error
                power = max(min(power, 1.0), 0.0)

                power = 1.0 - power

            self.fan.set_value(power)
            time.sleep(1)
        self.disabled = True
