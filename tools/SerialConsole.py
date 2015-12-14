#!/usr/bin/env python3
# -*- codinq: utf-8 -*-

import signal
import logging
from multiprocessing import JoinableQueue

from ertza.Machine import Machine
from ertza.ConfigParser import ConfigParser
from ertza.processors.serial.SerialServer import SerialServer
from ertza.processors.SerialProcessor import SerialProcessor


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s \
                        %(levelname)-8s %(message)s',
                        datefmt='%Y/%m/%d %H:%M:%S')

    m = Machine()
    c = ConfigParser()
    c.add_section('serial')
    dev = input('Serial device [/dev/ttyUSB0] ? ')
    baud = input('Baudrate [115200] ? ')

    c['serial']['listen_device'] = dev if dev is not None else '/dev/ttyUSB0'
    c['serial']['baudrate'] = baud if baud is not '' else '115200'

    m.config = c
    m.commands = JoinableQueue(10)
    m.unbuffered_commands = JoinableQueue(10)
    m.synced_commands = JoinableQueue()

    m.serial_processor = SerialProcessor(m)
    s = SerialServer(m)
    s.start()

    signal.pause()
