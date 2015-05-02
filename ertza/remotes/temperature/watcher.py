# -*- coding: utf-8 -*-

#from ertza.utils.adafruit_i2c import Adafruit_I2C
#from .temp_chart import NTCLE100E3103JB0 as temp_chart

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

#TEMP_PINS = (
#        '/sys/bus/iio/devices/iio:device0/in_voltage0_raw', #AIN0
#        '/sys/bus/iio/devices/iio:device0/in_voltage1_raw', #AIN1
#        )
#TEMP_TARGET = (40.0, 40.0,) # in °C
#FAN_PINS = (0, 1)

#TEMP_TABLE = temp_chart

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
