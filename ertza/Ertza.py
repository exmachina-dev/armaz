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
import queue

from ConfigParser import ConfigParser
from Machine import Machine
from OscProcessor import OscProcessor
from OscServer import OscServer

from PWM import PWM
try:
    from Thermistor import Thermistor
    NO_TH = False
except ImportError:
    NO_TH = True

from Fan import Fan
from Switch import Switch
from TempWatcher import TempWatcher
from Led import Led

version = "0.0.2~Firstimer"

_DEFAULT_CONF = "/etc/ertza/default.conf"
_MACHINE_CONF = "/etc/ertza/machine.conf"
_CUSTOM_CONF = "/etc/ertza/custom.conf"

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s \
                    %(levelname)-8s %(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S')


class Ertza(object):
    """
    Main class for ertza.

    Handle log, configuration, startup and dispatch others tasks to
    various processes
    """

    def __init__(self, *agrs, **kwargs):
        """ Init """
        logging.info("Ertza initializing. Version: " + version)

        machine = Machine()
        self.machine = machine

        if not os.path.isfile(_DEFAULT_CONF):
            logging.error(_DEFAULT_CONF + " does not exist, exiting.")
            sys.exit(1)

        machine.config = ConfigParser(_DEFAULT_CONF,
                                      _MACHINE_CONF,
                                      _CUSTOM_CONF)

        machine.config.load_variant()

        self._config_leds()
        for l in self.machine.leds:
            if l.function == 'status':
                l.set_blink(500)

        # Get loglevel from config file
        level = self.machine.config.getint('system', 'loglevel')
        if level > 0:
            logging.info("Setting loglevel to %d" % level)
            logging.getLogger().setLevel(level)

        drv = machine.init_driver()
        if drv:
            logging.info("Loaded %s driver for machine" % drv)
        else:
            logging.error("Unable to find driver, exiting.")
            sys.exit(1)

        PWM.set_frequency(1000)

        if not NO_TH:
            self._config_thermistors()
        self._config_fans()
        self._config_external_switches()

        # Create queue of commands
        self.machine.commands = JoinableQueue(10)
        self.machine.unbuffered_commands = JoinableQueue(10)
        self.machine.sync_commands = JoinableQueue()

        self.machine.osc_processor = OscProcessor(self.machine)

        machine.comms["OSC"] = OscServer(self.machine)

    def start(self):
        """ Start the processes """
        self.running = True

        # Start the processes
        commands_thread = Thread(target=self.loop,
                                 args=(self.machine.commands, "command"))
        unbuffered_commands_thread = Thread(target=self.loop,
                                            args=(self.machine.unbuffered_commands,
                                                  "unbuffered"))
        synced_commands_thread = Thread(target=self.eventloop,
                                        args=(self.machine.sync_commands, "sync"))

        commands_thread.deamon = True
        unbuffered_commands_thread.deamon = True
        synced_commands_thread.deamon = True

        commands_thread.start()
        unbuffered_commands_thread.start()
        # synced_commands_thread.start()

        self.machine.start()

        for name, comm in self.machine.comms.items():
            comm.start()
            logging.info("%s communication module started" % name)

        logging.info("Ertza ready")
        for l in self.machine.leds:
            if l.function == 'status':
                l.set_blink(50)

    def loop(self, machine_queue, name):
        """ When a new command comes in, execute it """
        p = self.machine.osc_processor  # Right now, only osc is implemented

        try:
            while self.running:
                try:
                    command = machine_queue.get(block=True, timeout=1)
                except queue.Empty:
                    continue

                logging.debug("Executing %s from %s" % (command.target, name))

                self._execute(command, p)

                self.machine.reply(command)

                machine_queue.task_done()
        except Exception as e:
            logging.exception("Exception in %s loop: %s" % (name, e))

    def eventloop(self, machine_queue, name):
        """ When a new event comes in, execute the pending gcode """
        p = self.machine.osc_processor  # Right now, only osc is implemented

        try:

            while self.running:
                # Returns False on timeout, else True
                if self.machine.wait_until_sync_event():
                    try:
                        command = machine_queue.get(block=True, timeout=1)
                    except queue.Empty:
                        continue

                    self._synchronize(command, p)
                    logging.info("Event handled for %s from %s %s" % (
                        command.code(), name, command.message))
                    machine_queue.task_done()
        except Exception:
            logging.exception("Exception in {} eventloop: ".format(name))

    def exit(self):
        self.machine.exit()

        for f in self.machine.fans:
            f.set_value(0)

        for l in self.machine.leds:
            l.set_trigger('default-on')

    def _config_thermistors(self):

        # Get available thermistors
        self.machine.thermistors = []
        if self.machine.config.getboolean('thermistors', 'got_thermistors'):
            th_p = 0

            while self.machine.config.has_option("thermistors",
                                                 "port_TH%d" % th_p):
                adc_channel = self.machine.config.getint("thermistors",
                                                         "port_TH%d" % th_p)
                self.machine.thermistors.append(Thermistor(adc_channel,
                                                           "TH%d" % th_p))
                logging.debug(
                    "Found thermistor TH%d at ADC channel %d" % (th_p,
                                                                 adc_channel))
                th_p += 1

    def _config_fans(self):

        self.machine.fans = []

        if self.machine.config.getboolean('fans', 'got_fans'):
            f_p = 0
            while self.machine.config.has_option("fans", "address_F%d" % f_p):
                fan_channel = self.machine.config.getint("fans",
                                                         "address_F%d" % f_p)
                self.machine.fans.append(Fan(fan_channel))
                logging.debug(
                    "Found fan F%d at channel %d" % (f_p, fan_channel))
                f_p += 1

        for f in self.machine.fans:
            f.set_value(1)

        # Connect fans to thermistors
        if self.machine.fans and not NO_TH:
            self.machine.temperature_watchers = []
            for t, therm in enumerate(self.machine.thermistors):
                for f, fan in enumerate(self.machine.fans):
                    if self.machine.config.getboolean("temperature_watchers",
                                                      "connect_TH%d_to_F%d" %
                                                      (t, f),
                                                      fallback=False):
                        tw = TempWatcher(therm, fan,
                                         "TempWatcher-%d-%d" % (t, f))
                        tw.set_target_temperature(
                            self.machine.config.getfloat(
                                "thermistors", "target_temperature_TH%d" % t))
                        tw.set_max_temperature(
                            self.machine.config.getfloat(
                                "thermistors", "max_temperature_TH%d" % t))
                        tw.enable()
                        self.machine.temperature_watchers.append(tw)

    def _config_external_switches(self):

        # Create external switches
        self.machine.switches = []
        esw_p = 0
        while self.machine.config.has_option("switches",
                                             "keycode_ESW%d" % esw_p):
            esw_n = "ESW%d" % esw_p
            esw_kc = self.machine.config.getint("switches",
                                                "keycode_%s" % esw_n)
            name = self.machine.config.get("switches",
                                           "name_%s" % esw_n, fallback=esw_n)
            esw = Switch(esw_kc, name)
            esw.invert = self.machine.config.getboolean("switches",
                                                        "invert_%s " % esw_n)
            esw.function = self.machine.config.get("switches",
                                                   "function_%s " % esw_n)
            self.machine.switches.append(esw)
            logging.debug("Found switch %s at keycode %d" % (name, esw_kc))
            esw_p += 1

    def _config_leds(self):

        # Create leds
        self.machine.leds = []
        if self.machine.config.getboolean('leds', 'got_leds'):
            led_i = 0
            while self.machine.config.has_option("leds", "file_L%d" % led_i):
                led_n = "L%d" % led_i
                led_f = self.machine.config.get("leds", "file_%s" % led_n)
                led_fn = self.machine.config.get("leds", "function_%s" % led_n,
                                                 fallback=None)
                led = Led(led_f, led_fn)
                led_t = self.machine.config.get("leds", "trigger_%s" % led_n,
                                                fallback='none')
                led.set_trigger(led_t)
                if led_t == "timer":
                    led.set_blink(self.machine.config.get("leds",
                                                          "blink_%s" % led_n,
                                                          fallback='500'))
                self.machine.leds.append(led)
                logging.debug("Found led %s, trigger: %s" % (led_n, led_t))
                led_i += 1

    def _execute(self, c, p):
        p.execute(c)


def main():
    e = Ertza()

    def signal_handler(signal, frame):
        e.exit()

    signal.signal(signal.SIGINT, signal_handler)

    e.start()

    signal.pause()


def profile():
    import yappi
    yappi.start()
    main()
    yappi.get_func_stats().print_all()

if __name__ == '__main__':
    _DEFAULT_CONF = '../conf/default.conf'
    _MACHINE_CONF = '../conf/fake.conf'
    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        profile()
    else:
        main()
