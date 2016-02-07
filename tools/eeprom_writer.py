#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import datetime
import struct
import bitstring as bs
from collections import OrderedDict


eeprom = '/sys/bus/i2c/devices/2-0054/eeprom'

available_variants = (
    'ARMAZ.HEAVY',
    'ARMAZ.FAST',
    'ARMAZ.FLAT',
)

pin_usage = OrderedDict()

#          U  D  S  R  UD PE MM
_unused = (0, 0, 0, 0, 0, 0, 0)
pin_usage['UART2_RXD'] = _unused
pin_usage['UART2_TXD'] = _unused
pin_usage['I2C1_SDA'] = _unused
pin_usage['I2C1_SCL'] = _unused
pin_usage['GPIO0_7'] = _unused
pin_usage['UART4_CTSN'] = _unused
pin_usage['UART4_RTSN'] = _unused
pin_usage['UART5_CTSN'] = _unused
pin_usage['UART5_RTSN'] = _unused
pin_usage['I2C2_SCL'] = (1, 2, 0, 1, 0, 0, 3,)
pin_usage['I2C2_SDA'] = (1, 3, 0, 1, 0, 0, 3,)
pin_usage['UART1_RXD'] = _unused
pin_usage['UART1_TXD'] = _unused
pin_usage['CLKOUT2'] = _unused
pin_usage['EHRPWM2A'] = _unused
pin_usage['EHRPWM2A'] = _unused
pin_usage['GPIO0_26'] = _unused
pin_usage['GPIO0_27'] = _unused
pin_usage['UART4_RXD'] = (1, 1, 0, 1, 1, 0, 6,)
pin_usage['UART4_TXD'] = _unused
pin_usage['GPIO1_0'] = _unused
pin_usage['GPIO1_1'] = _unused
pin_usage['GPIO1_2'] = _unused
pin_usage['GPIO1_3'] = _unused
pin_usage['GPIO1_4'] = _unused
pin_usage['GPIO1_5'] = _unused
pin_usage['GPIO1_6'] = _unused
pin_usage['GPIO1_7'] = _unused
pin_usage['GPIO1_12'] = _unused
pin_usage['GPIO1_13'] = _unused
pin_usage['GPIO1_14'] = _unused
pin_usage['GPIO1_15'] = _unused
pin_usage['GPIO1_16'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['GPIO1_17'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['EHRPWM1A'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['EHRPWM1B'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['GPIO1_28'] = (1, 2, 0, 0, 1, 0, 7,)
pin_usage['GPIO1_29'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['GPIO1_30'] = _unused
pin_usage['GPIO1_31'] = _unused
pin_usage['GPIO2_1'] = _unused
pin_usage['TIMER4'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['TIMER5'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['TIMER6'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['TIMER7'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['GPIO2_6'] = _unused
pin_usage['GPIO2_7'] = _unused
pin_usage['GPIO2_8'] = _unused
pin_usage['GPIO2_9'] = _unused
pin_usage['GPIO2_10'] = _unused
pin_usage['GPIO2_11'] = _unused
pin_usage['GPIO2_12'] = _unused
pin_usage['GPIO2_13'] = _unused
pin_usage['UART5_TXD'] = (1, 2, 0, 0, 1, 0, 4,)
pin_usage['UART5_RXD'] = (1, 1, 0, 0, 0, 0, 4,)
pin_usage['UART3_CTSN'] = _unused
pin_usage['UART3_RTSN'] = _unused
pin_usage['GPIO2_22'] = _unused
pin_usage['GPIO2_23'] = _unused
pin_usage['GPIO2_24'] = _unused
pin_usage['GPIO2_25'] = _unused
pin_usage['SPI1_D0'] = (1, 1, 0, 1, 1, 0, 3,)
pin_usage['SPI1_D1'] = (1, 2, 0, 1, 1, 0, 3,)
pin_usage['SPI1_CS0'] = (1, 2, 0, 1, 1, 0, 3,)
pin_usage['GPIO3_19'] = (1, 1, 0, 1, 1, 0, 7,)
pin_usage['SPI1_SCLK'] = (1, 3, 0, 1, 1, 0, 3,)
pin_usage['GPIO3_21'] = _unused
pin_usage['AIN0'] = (1, 1, 0, 0, 0, 0, 0,)
pin_usage['AIN1'] = (1, 1, 0, 0, 0, 0, 0,)
pin_usage['AIN2'] = (1, 1, 0, 0, 0, 0, 0,)
pin_usage['AIN3'] = _unused
pin_usage['AIN4'] = _unused
pin_usage['AIN5'] = _unused


def check_dict(chick_dict, orig_dict):
    for key, value in check_dict.items():
        try:
            if value == orig_dict[key]:
                print('\t\t{:>16}: {:<32}\tOk'.format(key, value))
            else:
                print('\t\t{:>16}: {:<32}\tError: '
                      'original value {}'.format(key, value, orig_dict[key]))
        except KeyError:
            print('\t\tUnrecognized key: {}'.format(key))


def serial_gen():
    isodate = datetime.date.today().isocalendar()
    yy = str(isodate[0])[2:]
    ww = str(isodate[1]).rjust(2, '0')
    asco = 'ARCP'
    print('Current date: W: {} Y: {}'.format(ww, yy))
    nnnn = input('Unit number manufactured in the current week (1-9999): ').rjust(4, '0')

    sn = ww + yy + asco + nnnn

    return sn

rev = input('Revision number (up to 4 chars) ? ')
if rev and len(rev) > 4:
    raise ValueError('Revision number is too long')

print('\nAvailable variants:')
for i, v in enumerate(available_variants):
    print('\t[{}] {}'.format(i, v))
var_i = input('\nVariant (0..{}) ? '.format(len(available_variants)-1))

try:
    variant = available_variants[int(var_i)]
except KeyError:
    print('Invalid variant number. Exiting.')
    sys.exit()

data = OrderedDict()
data['eeprom_header'] = b'\xAA\x55\x33\xEE'
data['eeprom_rev'] = 'A1'.encode()
data['name'] = 'ArmazCape - Rev {}'.format(rev).ljust(32).encode()
data['revision'] = rev.rjust(4, '0').encode() if rev else '0000'.encode()
data['manufacturer'] = 'ExMachina'.ljust(16).encode()
data['partnumber'] = 'ARMAZCAPE'.ljust(16).encode()
data['nb_pins_used'] = struct.pack('>h', 92)
data['serialnumber'] = serial_gen().encode()

power_data = OrderedDict()
power_data['VDD_3V3B_current'] = struct.pack('>h', 400)
power_data['VDD_5V_current'] = struct.pack('>h', 400)
power_data['SYS_5V_current'] = struct.pack('>h', 0)
power_data['DC_supplied_current'] = struct.pack('>h', 2000)

custom_data = OrderedDict()
custom_data['variant'] = variant.ljust(16).encode()

with open(eeprom, 'wb') as e:
    print('Erasing existing data...', end='')
    e.write(b'\x00'*260)
    print(' Done.')

    e.seek(0)
    print('Writing cape data...', end='')
    for d in data.items():
        e.write(d[1])
    print(' Done.')

    pin_format = 'uint:1, uint:2, pad:6, uint:1, uint:1, uint:1, uint:1, uint:3'
    e.seek(88)
    print('Writing pins data...', end='')
    for p in pin_usage.items():
        if len(p[1]) != 7:
            print('Invalid pin config: {0}, {1}'.format(*p))
            continue

        p_b = bs.pack(pin_format, *p[1])
        e.write(p_b.bytes)
    print(' Done.')

    e.seek(236)
    print('Writing power data...', end='')
    for d in power_data.items():
        e.write(d[1])
    print(' Done.')

    e.seek(244)
    print('Writing custom data...', end='')
    for d in custom_data.items():
        e.write(d[1])
    print(' Done.')

with open(eeprom, 'rb') as e:
    print('Reading EEPROM...', end='')
    edata = e.read(260)
    print(' Done.')

    print('Checking EEPROM data...')
    edata = {
        'eeprom_header': data[0:4],
        'eeprom_rev': data[4:6].decode(),
        'name': data[6:38].strip().decode(),
        'revision': data[38:42].decode(),
        'manufacturer': data[42:58].strip().decode(),
        'partnumber': data[58:74].strip().decode(),
        'nb_pins_used': struct.unpack('>h', data[74:76])[0],
        'serialnumber': data[76:88].decode(),
    }

    print('\tChecking cape data...')
    check_dict(edata, data)
    print('\tDone.',)

    edata = {
        'pin_data': data[88:236],
    }
    edata = {
        'VDD_3V3B_current': struct.unpack('>h', data[236:238])[0],
        'VDD_5V_current': struct.unpack('>h', data[238:240])[0],
        'SYS_5V_current': struct.unpack('>h', data[240:242])[0],
        'DC_supplied_current': struct.unpack('>h', data[242:244])[0],
    }

    print('\tChecking power data...')
    check_dict(edata, powerdata)
    print('\tDone.',)

    edata = {
        'variant': data[244:260].strip().decode(),
    }
    print('\tChecking custom data...')
    check_dict(edata, custom_data)
    print('\tDone.',)
    print('EEPROM check done.')


