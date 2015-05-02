# -*- coding: utf-8 -*-

#from ertza.utils.adafruit_i2c import Adafruit_I2C
import time
import subprocess

from ...config import ConfigRequest
from ...errors import RemoteError
from ..modbus import ModbusRequest
#from .temp_chart import NTCLE100E3103JB0 as temp_chart
from .event_watcher import EventWatcher as SwitchHandler

## PWM config
## code taken from https://bitbucket.org/intelligentagent/redeem
#PCA9685_MODE1 = 0x0
#PCA9685_PRESCALE = 0xFE
#
#
#kernel_version = subprocess.check_output(["uname", "-r"]).strip()
#[major, minor, rev] = kernel_version.decode('UTF-8').split("-")[0].split(".")
#try:
#    if int(minor) >= 14 :
#        pwm = Adafruit_I2C(0x70, 2, False)  # Open device
#    else:
#        pwm = Adafruit_I2C(0x70, 1, False)  # Open device
#except OSError:
#    pwm = None
#    print('Unable to open pwm device.')
#
#
#if pwm:
#    pwm.write8(PCA9685_MODE1, 0x01)         # Reset
#    time.sleep(0.05)                        # Wait for reset

SWITCH_PINS = (("GPIO0_30", 'switch_0', 112), ("GPIO0_31", 'switch_1', 113))
#TEMP_PINS = (
#        '/sys/bus/iio/devices/iio:device0/in_voltage0_raw', #AIN0
#        '/sys/bus/iio/devices/iio:device0/in_voltage1_raw', #AIN1
#        )
#TEMP_TARGET = (40.0, 40.0,) # in °C
#FAN_PINS = (0, 1)

#TEMP_TABLE = temp_chart

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

        self.switchs = {}
        self.switchs_actions = {}

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
                #self.create_temp_watchers()
                if self.restart_event:
                    self.restart_event.clear()
            except (NameError, RuntimeError) as e:
                raise RemoteError(
                        'Error configuring pins, am I on a beaglebone ?',
                        self.lg) from e
                if not self.fake_mode:
                    self.lg.warn('Starting failed. Fallback to fake mode.')
                    self.fake_mode = True
                    self.run()

        #if not self.fake_mode:
            #self.update_pid()

    def create_switch_pins(self):
        if not self.fake_mode:
            SwitchHandler.callback = self.switch_callback
            SwitchHandler.inputdev = '/dev/input/event1'
            for p in SWITCH_PINS:
                a = self.config_request.get(p[1], 'action', None)
                r = self.config_request.get(p[1], 'reverse', False)
                self.switchs[p[1]] = SwitchHandler(*p, invert=r)
                self.switchs_actions[p[1]] = a
            self.switchs = tuple(sw)
            return True
        return False

    def switch_callback(self, event):
        state = bool(event.state)
        if self.switchs_actions[event.name] == 'reverse':
            self.lg.info('Reversing direction.')
            self.mdb_request.reverse(state)
        elif self.switchs_actions[event.name] == 'activate':
            self.lg.info('Activating control.')
            self.mdb_request.activate(state)

    def create_temp_watchers(self):
        if TEMP_PINS and not self.fake_mode:
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
            if p.update_state(): # if something change, trigger
                self.mdb_request.trigger(p.action, p.state)


class TempWatcher(object):
    def __init__(self, sensor, fan, target_temp):
        self.sensor = sensor
        self.beta = 3977
        self.fan = Fan(fan)
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
        """ Return the temperature in degrees celsius """
        with open(self.sensor, "r") as file:
            try:
                voltage = (float(file.read().rstrip()) / 4095.0) * 1.8
                res_val = self.voltage_to_resistance(voltage)  # Convert to resistance
                return self.resistance_to_degrees(res_val) # Convert to degrees
            except IOError as e:
                logging.error("Unable to get ADC value ({0}): {1}".format(e.errno, e.strerror))
                return -1.0

    def resistance_to_degrees(self, resistor_val):
        """ Return the temperature nearest to the resistor value """
        return resistor_val

    def voltage_to_resistance(self, v_sense):
        """ Convert the voltage to a resistance value """
        if v_sense == 0 or (abs(v_sense - 1.8) < 0.001):
            return 10000000.0
        return 4700.0 / ((1.8 / v_sense) - 1.0)

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
        pass


class Fan(object):
    @staticmethod
    def set_PWM_frequency(freq):
        """ Set the PWM frequency for all fans connected on this PWM-chip """
        prescaleval = 25000000
        prescaleval /= 4096
        prescaleval /= float(freq)
        prescaleval -= 1
        prescale = int(prescaleval + 0.5)

        oldmode = pwm.readU8(PCA9685_MODE1)
        newmode = (oldmode & 0x7F) | 0x10
        if pwm:
            pwm.write8(PCA9685_MODE1, newmode)
            pwm.write8(PCA9685_PRESCALE, prescale)
            pwm.write8(PCA9685_MODE1, oldmode)
            time.sleep(0.05)
            pwm.write8(PCA9685_MODE1, oldmode | 0xA1)

    def __init__(self, channel):
        """ Channel is the channel that the fan is on (0-7) """
        self.channel = channel

    def set_value(self, value):
        """ Set the amount of on-time from 0..1 """
        #off = min(1.0, value)
        off = int(value*4095)
        byte_list = [0x00, 0x00, off & 0xFF, off >> 8]
        if pwm:
            pwm.writeList(0x06+(4*self.channel), byte_list)
