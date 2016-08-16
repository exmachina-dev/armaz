# -*- coding: utf-8 -*-

import os.path


LedModes = (
    'none', 'default-on', 'oneshot', 'timer',
    'nand-disk', 'mmc0', 'mmc1', 'heartbeat', 'cpu0', 'gpio')


class Led(object):
    led_sys_path = '/sys/devices/platform/leds/leds'
    actions = ('on', 'off', 'flash', 'blink')
    leds = {}

    def __init__(self, led_folder, name=None, function=None):
        self.full_path = os.path.join(Led.led_sys_path, led_folder)
        self.trigger = os.path.join(self.full_path, 'trigger')
        self.delay_on = os.path.join(self.full_path, 'delay_on')
        self.delay_off = os.path.join(self.full_path, 'delay_off')
        self.brightness = os.path.join(self.full_path, 'brightness')

        self._function = function
        self._name = name or led_folder

        self.leds[self.name] = self

    def set_trigger(self, new_trigger):
        if new_trigger not in LedModes:
            raise ValueError('Wrong trigger supplied: {}'.format(new_trigger))

        with open(self.trigger, mode='w') as f:
            f.write(str(new_trigger))

    def set_brightness(self, new_brightness=255):
        with open(self.brightness, mode='w') as f:
            f.write(str(new_brightness))

    def set_delays(self, on=1000, off=-1):
        if on is not None:
            with open(self.delay_on, mode='w') as f:
                f.write(str(on))
        if off is not None:
            if off <= 0:
                off = on
            with open(self.delay_off, mode='w') as f:
                f.write(str(off))

    def blink(self, new_delay):
        if new_delay > 0:
            self.set_trigger('timer')
            self.set_delays(new_delay)
        else:
            self.set_trigger('none')

    def on(self):
        self.set_trigger('default-on')

    def off(self):
        self.set_trigger('none')

    def flash(self, delay=1000):
        self.set_trigger('oneshot')
        self.set_delays(delay)

    @property
    def function(self):
        return self._function

    @property
    def name(self):
        return self._name

    @classmethod
    def set_all_leds(cls, action=None, delay=1000):
        cls.set_for_leds(cls.leds.values(), action, delay)

    @classmethod
    def set_status_leds(cls, action=None, delay=1000):
        status_leds = (led for led in cls.leds.values() if led.function == 'status')

        cls.set_for_leds(status_leds, action, delay)

    @classmethod
    def set_error_leds(cls, action=None, delay=1000):
        error_leds = (led for led in cls.leds.values() if led.function == 'error')

        cls.set_for_leds(error_leds, action, delay)

    @classmethod
    def set_for_leds(cls, leds, action, delay):
        if action not in cls.actions:
            raise ValueError('Unrecognized action: {}'.format(action))

        for l in leds:
            try:
                getattr(l, action)(delay)
            except TypeError:
                getattr(l, action)()

    def __del__(self):
        self.leds.pop(self.name, None)

if __name__ == '__main__':
    import time

    l2 = Led('beaglebone:green:usr2')

    l2.set_trigger('default-on')

    time.sleep(5)

    l2.set_trigger('delay-on')
    l2.set_blink(50)

    time.sleep(5)

    l2.set_trigger('heartbeat')
