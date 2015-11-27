# -*- coding: utf-8 -*-

import logging

_ADC_PATH = "/sys/bus/iio/devices/iio:device0"

class Thermistor(object):
    def __init__(self, pin, name):
        self.pin = "%s/in_voltage%d_raw" % (_ADC_PATH, pin)
        self.name = name

    @property
    def temperature(self):
        with open(self.pin, "r") as f:
            try:
                temp = float(f.read().split("t=")[-1]) / 1000.0
            except IOError:
                logging.warn("Unable to get temperature from %s" % self.name)
                return -1
        return temp
