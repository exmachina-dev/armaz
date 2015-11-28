#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Main class for ertza

import logging
import os
import os.path
import sys
import signal
from threading import Thread
from multiprocessing import JoinableQueue

from ConfigParser import ConfigParser
from Machine import Machine
from PWM import PWM
from Thermistor import Thermistor
from Fan import Fan
from TempWatcher import TempWatcher

version = "0.0.2~Firstimer"

_DEFAULT_CONF = "/etc/ertza/default.conf"
_MACHINE_CONF = "/etc/ertza/machine.conf"
_CUSTOM_CONF = "/etc/ertza/custom.conf"

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S')


class Ertza(object):
    """
    Main class for ertza.

    Handle log, configuration, startup and dispatch others tasks to various processes
    """

    def __init__(self, *agrs, **kwargs):
        """ Init """
        logging.info("Ertza initializing. Version: " + version)

        machine = Machine()
        self.machine = machine

        if not os.path.isfile(_DEFAULT_CONF):
            logging.error(_DEFAULT_CONF + " does not exist, exiting.")
            sys.exit()

        machine.config = ConfigParser(_DEFAULT_CONF, _MACHINE_CONF, _CUSTOM_CONF)

        # Get loglevel from config file
        level = self.machine.config.getint('system', 'loglevel')
        if level > 0:
            logging.info("Setting loglevel to %d" % level)
            logging.getLogger().setLevel(level)

        PWM.set_frequency(100)

        # Get available thermistors
        machine.thermistors = []
        th_p = 0
        while machine.config.has_option("thermistors", "port_TH%d" % th_p):
            adc_channel = machine.config.getint("thermistors", "port_TH%d" % th_p)
            machine.thermistors.append(Thermistor(adc_channel, "TH%d" % th_p))
            logging.debug("Found thermistor TH%d at ADC channel %d" % (th_p, adc_channel))
            th_p += 1


        machine.fans = None
        if self.machine.config.getboolean('fans', 'got_fans'):
            self.machine.fans = []
            f_p = 0
            while machine.config.has_option("fans", "address_F%d" % f_p):
                fan_channel = machine.config.getint("fans", "address_F%d" % f_p)
                machine.fans.append(Fan(fan_channel))
                logging.debug("Found fan F%d at channel %d" % (f_p, fan_channel))
                f_p += 1

        for f in machine.fans:
            f.set_value(100)

        # Connect fans to thermistors
        if machine.fans:
            machine.temperature_watchers = []
            for t, therm in enumerate(machine.thermistors):
                for f, fan in enumerate(machine.fans):
                    if machine.config.getboolean("temperature_watchers",
                                                 "connect_TH%d_to_F%d" % (t, f),
                                                 fallback=False):
                        tw = TempWatcher(therm, fan, "TempWatcher-%d-%d" % (t, f))
                        tw.set_target_temperature(machine.config.getfloat("thermistors", "target_temperature_TH%d" % t))
                        tw.set_max_temperature(machine.config.getfloat("thermistors", "max_temperature_TH%d" % t))
                        tw.enable()
                        machine.temperature_watchers.append(tw)

        # Create queue of commands
        self.machine.commands = JoinableQueue(10)
        self.machine.unbuffered_commands = JoinableQueue(10)
        self.machine.sync_commands = JoinableQueue()

        # Create external switches
        machine.switches = []
        esw_p = 0
        while machine.config.has_option("switches", "keycode_ESW%d" % esw_p):
            esw_keycode = machine.config.getint("switches", "keycode_ESW%d" % esw_p)
            machine.switches.append(Switch(esw_keycode, "ESW%d" % esw_p))
            logging.debug("Found switch ESW%s at keycode %d" % (esw_p, esw_keycode))
            esw_p += 1


    def start(self):
        """ Start the processes """
        self.running = True

        # Start the processes
        thread0 = Thread(target=self.loop,
                         args=(self.machine.commands, "command"))
        thread1 = Thread(target=self.loop,
                         args=(self.machine.unbuffered_commands, "unbuffered"))
        thread2 = Thread(target=self.eventloop,
                         args=(self.machine.sync_commands, "sync"))

        thread0.deamon = True
        thread1.deamon = True
        thread2.deamon = True

        thread0.start()
        thread1.start()
        thread2.start()

        logging.info("Ertza ready")

    def loop(self, queue, name):
        pass

    def eventloop(self, queue, name):
        pass

    def exit(self):
        pass


def main():
    e = Ertza()

    def signal_handler(signal, frame):
        e.exit()

    signal.signal(signal.SIGINT, signal_handler)

    e.start()

    signal.pause()

if __name__ == '__main__':
    _DEFAULT_CONF = '../conf/default.conf'
    _MACHINE_CONF = '../conf/machine.conf'
    main()
