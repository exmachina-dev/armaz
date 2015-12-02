#!/usr/bin/env python
"""
A fan is for blowing stuff away. This one is for Replicape.

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

import time
from PWM import PWM


class Fan(PWM):

    def __init__(self, channel):
        """ Channel is the channel that the fan is on (0-7) """
        self.channel = channel

    def set_value(self, value):
        """ Set the amount of on-time from 0..1 """
        PWM.set_value(value, self.channel)

if __name__ == '__main__':
    import logging
    import signal
    from threading import Thread

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s \
                        %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M')

    PWM.set_frequency(100)

    fan0 = Fan(0)
    fan1 = Fan(1)

    exit_ev = False

    def sign_handler(signal, frame):
        exit_ev = True
        fan0.set_value(0)
        fan1.set_value(0)

    signal.signal(signal.SIGINT, sign_handler)

    def fan_thread():
        while not exit_ev:
            for i in range(1, 100):
                fan0.set_value(i/100.0)
                fan1.set_value((100-i)/100.0)
                time.sleep(0.1)
            for i in range(100, 1, -1):
                fan0.set_value(i/100.0)
                fan1.set_value((100-i)/100.0)
                time.sleep(0.1)

    t = Thread(target=fan_thread)
    t.daemon = True
    t.start()
    signal.pause()

