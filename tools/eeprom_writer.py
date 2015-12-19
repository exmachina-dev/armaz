#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import struct
from collections import OrderedDict


eeprom = '/sys/bus/i2c/devices/2-0054/eeprom'


def serial_gen():
    isodate = datetime.date.today().isocalendar()
    yy = str(isodate[0])[2:]
    ww = str(isodate[1]).rjust(2, '0')
    asco = 'ARCP'
    nnnn = input('Unit number manufactured in the current week (1-9999): ').rjust(4, '0')

    sn = ww + yy + asco + nnnn

    return sn

rev = input('Revision number (up to 4 chars)? ')
if rev and len(rev) > 4:
    raise ValueError('Revision number is too long')

data = OrderedDict()
data['eeprom_header'] = b'\xAA\x55\x33\xEE'
data['eeprom_rev'] = 'A1'.encode()
data['name'] = 'ArmazCape - Rev {}'.format(rev).ljust(32).encode()
data['revision'] = rev.rjust(4, '0').encode() if rev else '0000'.encode()
data['manufacturer'] = 'ExMachina'.ljust(16).encode()
data['partnumber'] = 'ARMAZCAPE'.ljust(16).encode()
data['nb_pins_used'] = struct.pack('>h', 92)
data['serialnumber'] = serial_gen().encode()

with open(eeprom, 'wb') as e:
    for d in data.items():
        e.write(d[1])
