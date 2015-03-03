# -*- coding: utf-8 -*-

from ...errors import SerialError

import serial

class RemoteControlLink(serial.Serial):
    def __init__(self, port=None, baudrate=57600):
        super(RemoteControlLink, self).__init__(port=port, baudrate=baudrate)
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.timeout = 0
        self.xonxoff = True

    def get_product_id(self):
        self.write('R')
        return self.read(5)

if __name__ == '__main__':
    s = RemoteControlLink('/dev/ttyO1')
    s.get_product_id()
