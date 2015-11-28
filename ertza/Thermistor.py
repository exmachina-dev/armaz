# -*- coding: utf-8 -*-

import numpy as np
from threading import Lock
import logging

from temp_chart import *

_ADC_PATH = "/sys/bus/iio/devices/iio:device0"

class Thermistor(object):

    temp_table = np.array(temp_chart['NTCLE100E3103JB0']).transpose()
    mutex = Lock()

    def __init__(self, pin, name):
        self.pin = "%s/in_voltage%d_raw" % (_ADC_PATH, pin)
        self.name = name

    @property
    def temperature(self):
        temp = -1.0
        Thermistor.mutex.acquire()

        try:
            with open(self.pin, "r") as f:
                voltage = (float(f.read().rstrip()) / 4095.0) * 1.8
                res_val = self.voltage_to_resistance(voltage)
                temp = self.resistance_to_degrees(res_val)
        except IOError as e:
            logging.warn("Unable to get temperature from %s" % self.name)
        finally:
            Thermistor.mutex.release()

        return temp

    def resistance_to_degrees(self, resistor_val):
        idx = (np.abs(Thermistor.temp_table[1] - resistor_val)).argmin()
        return Thermistor.temp_table[0][idx]

    def voltage_to_resistance(self, v_sense):
        if v_sense == 0 or (abs(v_sense - 1.8) < 0.001):
            return 10000000.0
        return 4700.0 / ((1.8 / v_sense) - 1.0)
