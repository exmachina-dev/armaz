# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
A class that listens for a button press
and sends an event if that happens.

Taken from https://bitbucket.org/intelligentagent/redeem

Author: Elias Bakken
email: elias(dot)bakken(at)gmail(dot)com
Website: http://www.thing-printer.com
License: GNU GPL v3: http://www.gnu.org/copyleft/gpl.html

 Redeem is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Redeem is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Redeem.  If not, see <http://www.gnu.org/licenses/>.
"""

from threading import Thread
import mmap
import struct
import re


class EventWatcher(object):

    PRU_ICSS = 0x4A300000 
    PRU_ICSS_LEN = 512 * 1024
    RAM2_START = 0x00012000

    callback = None                 # Override this to get events
    inputdev = "/dev/input/event0"  # File to listen to events

    def __init__(self, pin, key_code, name, **kwargs):
        self.pin = pin
        self.key_code = key_code
        self.name = name
        self.invert = False
        if 'invert' in kwargs:
            self.invert = kwargs['invert']
        self.hit = False
        self.state = None
        self.debounced = None

        self.debounce_time = 0
        self.last_time = 0
        if 'debounce_time' in kwargs:
            self.debounce_time = kwargs['debounce_time']

        if self.debounce_time:
            import time as t

    def get_gpio_bank_and_pin(self):
        matches = re.compile(r'GPIO([0-9])_([0-9]+)').search(self.pin)
        tup = matches.group(1, 2)
        tup = (int(tup[0]), int(tup[1]))
        return tup

    def get_pin(self):
        return self.pin

    def wait_for_event(self):
        evt_file = open(EventWatcher.inputdev, "rb")
        while True:
            evt = evt_file.read(16) # Read the event
            evt_file.read(16)       # Discard the debounce event (or whatever)
            code = evt[10]
            direction = "down" if evt[12] else "up"
            if code == self.key_code:
                if self.invert is True and direction == "down":
                    self.debounce(True)
                elif self.invert is False and direction == "up":
                    self.debounce(True)
                elif self.invert is True and direction == "up":
                    self.debounce(False)
                elif self.invert is False and direction == "down":
                    self.debounce(False)
                else:
                    self.hit = False
                    self.state = None

    def debounce(self, state):
        if self.debounce_time:
            if (t.time() - self.last_time) > self.debounce_time:
                self.debounced = True
            else:
                self.debounced = False

        self.state = state
        self.last_time = t.time()
        if EventWatcher.callback is not None:
            EventWatcher.callback(self)

    def read_value(self):
        """ Read the current endstop value from GPIO using PRU1 """
        with open("/dev/mem", "r+b") as f:
            ddr_mem = mmap.mmap(f.fileno(),
                                self.PRU_ICSS_LEN, offset=self.PRU_ICSS)
            state = struct.unpack('LL',
                                  ddr_mem[self.RAM2_START:self.RAM2_START + 8])
            if self.name == "switch_0":
                self.hit = bool(state[0] & (1 << 0))
            elif self.name == "switch_1":
                self.hit = bool(state[0] & (1 << 1))
            elif self.name == "switch_2":
                self.hit = bool(state[0] & (1 << 2))
            else:
                raise RuntimeError('Invalid switch name')
        return self.hit

    def __repr__(self):
        _v = {
                'p': self.pin, 'k': self.key_code, 'n': self.name,
                'i': self.invert, 'dt': self.debounce_time, 's': self.state,
                'd': self.debounced,}
        return('EventWatcher: {p} {k} {n}, inverted: {i}, debounce_time: {dt}, state: {s}, debounced: {d}'.format(_v))

    __str__ = __repr__

if __name__ == '__main__':
    def cb(event):
        print(event.name)
        print(event.state)

    EventWatcher.callback = cb
    ew = EventWatcher('GPIO3_30', 1, 'switch_0', True)
    ew.wait_for_event()
