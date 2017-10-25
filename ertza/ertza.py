#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Main class for ertza

import logging as lg
import os
import os.path
import sys
import signal
from threading import Thread
from multiprocessing import JoinableQueue
import queue

from .configparser import ConfigParser, ProfileError
from .machine import Machine, MachineError

from .processors import OscProcessor, SerialProcessor

from .processors.osc.server import OscServer
from .processors.serial.server import SerialServer
from .processors.serial.message import SerialCommandString

from .pwm import PWM
from .thermistor import Thermistor

from .fan import Fan
from .switch import Switch
from .tempwatcher import TempWatcher
from .led import Led

from .network_utils import EthernetInterface

version = "0.1.0~Siderunner"

_DEFAULT_CONF = "/etc/ertza/default.conf"
_MACHINE_CONF = "/etc/ertza/machine.conf"
_CUSTOM_CONF = "/etc/ertza/custom.conf"

console_logger = lg.StreamHandler()
console_formatter = lg.Formatter('%(asctime)s %(name)-36s '
                                 '%(levelname)-8s %(message)s',
                                 datefmt='%Y%m%d %H:%M:%S')

logger = lg.getLogger('ertza')
logger.addHandler(console_logger)
console_logger.setFormatter(console_formatter)


class Ertza(object):
    """
    Main class for ertza.

    Handle log, configuration, startup and dispatch others tasks to
    various processes
    """

    def __init__(self, *agrs, **kwargs):
        """ Init """
        logger.info("Ertza initializing. Version: " + version)

        machine = Machine()
        self.machine = machine
        machine.version = version

        if not os.path.isfile(_DEFAULT_CONF):
            logger.error(_DEFAULT_CONF + " does not exist, exiting.")
            sys.exit(1)

        c = None
        if 'config' in kwargs:
            c = kwargs['config']
        custom_conf = c[0] if c else _CUSTOM_CONF

        logger.info('Custom file: %s' % custom_conf)

        machine.config = ConfigParser(_DEFAULT_CONF,
                                      _MACHINE_CONF,
                                      custom_conf)

        self._config_leds()
        for l in self.machine.leds:
            if l.function == 'status':
                l.set_blink(500)

        # Get loglevel from config file
        level = self.machine.config.getint('system', 'loglevel', fallback=10)
        if level > 0:
            lg.getLogger('').setLevel(level)
            logger.setLevel(level)
            logger.info("Log level set to %d" % level)

        machine.cape_infos = machine.config.find_cape('ARMAZCAPE')

        if machine.cape_infos:
            name = machine.cape_infos['name']
            logger.info('Found cape %s with S/N %s' % (name, machine.serialnumber))
            SerialCommandString.SerialNumber = machine.serialnumber

        machine.config.load_variant()
        try:
            machine.config.load_profile()
        except ProfileError as e:
            logger.info('Unable to load profile: {!s}'.format(e))

        try:
            i = machine.config.get('machine', 'interface', fallback='eth1')
            logger.info('Configuring {} interface'.format(i))
            eth = None
            try:
                eth = EthernetInterface(i)
                logger.info('Setting interface {} to up'.format(i))
                eth.link_up()
                logger.info('Setting up default route'.format(i))
                eth.add_route('default')
            except Exception as e:
                logger.error(e)

            ip = machine.config.get('machine', 'ip_address', fallback=None)
            if eth:
                try:
                    if not ip:
                        ip = '10'
                        for byte in eth.mac_address.split(':')[3:6]:
                            ip += '.{}'.format(int('0x{}'.format(byte), base=0))
                            ip += '/8'

                    logger.info('Adding ip {} to {}'.format(ip, i))
                    eth.add_ip(ip)
                except Exception as e:
                    logger.error(e)
            else:
                logger.warn('Specified interface is not available: {}'.format(i))
            machine.ethernet_interface = eth
        except IndexError:
            logger.warn('No IP address found')

        drv = machine.init_driver()
        if drv:
            logger.info("Loaded %s driver for machine" % drv)
        else:
            logger.error("Unable to find driver, exiting.")
            sys.exit(1)

        self._config_thermistors()
        self._config_fans()
        self._config_external_switches()

        # Create queue of commands
        self.machine.commands = JoinableQueue(10)
        self.machine.unbuffered_commands = JoinableQueue(10)
        self.machine.sync_commands = JoinableQueue()

        if not machine.config.get('osc', 'disable', fallback=False):
            machine.processors['OSC'] = OscProcessor(self.machine)
            machine.comms['OSC'] = OscServer(self.machine)

        if not machine.config.get('serial', 'disable', fallback=False):
            machine.processors['Serial'] = SerialProcessor(self.machine)
            machine.comms['Serial'] = SerialServer(self.machine)

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
            logger.info("%s communication module started" % name)

        try:
            self.machine.load_startup_mode()
        except MachineError as e:
            logger.error(str(e))

        for l in self.machine.leds:
            if l.function == 'status':
                l.set_blink(50)

        logger.info("Ertza ready")

    def loop(self, machine_queue, name):
        """ When a new command comes in, execute it """

        try:
            while self.running:
                try:
                    message = machine_queue.get(block=True, timeout=1)
                except queue.Empty:
                    continue

                logger.debug("Executing %s from %s" % (message.command, name))

                try:
                    p = self.machine.processors[message.protocol]
                except KeyError:
                    raise KeyError('Unable to get %s processor' % message.protocol)

                try:
                    self._execute(message, p)
                    self.machine.reply(message)
                finally:
                    machine_queue.task_done()
        except Exception as e:
            logger.exception("Exception in %s loop: %s" % (name, e))

    def eventloop(self, machine_queue, name):
        """ When a new event comes in, execute the pending gcode """

        while self.running:
            try:
                # Returns False on timeout, else True
                if self.machine.wait_until_sync_event():
                    try:
                        message = machine_queue.get(block=True, timeout=1)
                    except queue.Empty:
                        continue

                    try:
                        p = self.machine.processors[message.protocol]
                    except KeyError:
                        raise KeyError('Unable to get %s processor' % message.protocol)

                    self._synchronize(message, p)

                    logger.info("Event handled for %s from %s %s" % (
                        message.target, name, message))
                    machine_queue.task_done()
            except Exception:
                logger.exception("Exception in {} eventloop: ".format(name))

    def exit(self):
        self.machine.exit()

        self.running = False

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
                try:
                    adc_channel = self.machine.config.getint("thermistors",
                                                            "port_TH%d" % th_p)
                    therm = Thermistor(adc_channel, 'TH{}'.format(th_p))
                    self.machine.thermistors.append(therm)
                    logger.debug('Found thermistor TH{} '
                                'at ADC channel {}'.format(th_p, adc_channel))
                    th_p += 1
                except Exception as e:
                    logger.warn('Unable to configure thermistor TH{}: {!s}'.format(th_p, e))

    def _config_fans(self):
        self.machine.fans = []

        # Get available fans
        if self.machine.config.getboolean('fans', 'got_fans'):
            PWM.set_frequency(1560)

            f_p = 0
            while self.machine.config.has_option("fans", "address_F%d" % f_p):
                try:
                    fan_channel = self.machine.config.getint("fans",
                                                            "address_F%d" % f_p)
                    fan = Fan(fan_channel)
                    fan.min_speed = float(self.machine.config.get(
                        "fans", 'min_speed_F{}'.format(f_p), fallback=0.0))
                    fan.set_value(1)
                    self.machine.fans.append(fan)
                    logger.debug(
                        "Found fan F%d at channel %d" % (f_p, fan_channel))
                    f_p += 1
                except Exception as e:
                    logger.warn('Unable to configure fan F{}: {!s}'.format(f_p, e))

        th_cf = self.machine.config["thermistors"]
        tw_cf = self.machine.config["temperature_watchers"]

        # Connect fans to thermistors
        if self.machine.fans:
            self.machine.temperature_watchers = []

            for t, therm in enumerate(self.machine.thermistors):
                for f, fan in enumerate(self.machine.fans):
                    if tw_cf.getboolean("connect_TH{}_to_F{}".format(t, f),
                                        fallback=False):
                        tw = TempWatcher(therm, fan,
                                         "TempWatcher-{}-{}".format(t, f))
                        tw.set_target_temperature(float(
                            th_cf.get("target_temperature_TH%d" % t)))
                        tw.set_max_temperature(float(
                            th_cf.get("max_temperature_TH%d" % t)))
                        tw.interval = float(th_cf.get('update_interval_TH{}'.format(t),
                                                      fallback=5))
                        tw.enable()
                        self.machine.temperature_watchers.append(tw)
        elif self.machine.thermistors:
            self.machine.temperature_watchers = []
            for t, therm in enumerate(self.machine.thermistors):
                tw = TempWatcher(therm, None, "TempLogger-%d" % t)
                tw.set_max_temperature(float(
                    th_cf.get("max_temperature_TH%d" % t)))
                tw.interval = float(th_cf.get('update_interval_TH{}'.format(t),
                                              fallback=5))
                tw.enable(mode=False)
                self.machine.temperature_watchers.append(tw)

    def _config_external_switches(self):
        Switch.callback = self.machine.switch_callback

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
                                                        "invert_%s" % esw_n)
            esw.function = self.machine.config.get("switches",
                                                   "function_%s" % esw_n)
            self.machine.switches.append(esw)
            logger.debug("Found switch %s at keycode %d" % (name, esw_kc))
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
                logger.debug("Found led %s, trigger: %s" % (led_n, led_t))
                led_i += 1

    def _execute(self, c, p):
        p.execute(c)


def main(parent_args=None):
    import argparse

    parser = argparse.ArgumentParser(prog='ertza')
    parser.add_argument('--config', nargs=1, help='use CONFIG as custom config file')

    if parent_args:
        args, args_remaining = parser.parse_known_args(parent_args)
    else:
        args, args_remaining = parser.parse_known_args()

    e = Ertza(**vars(args))

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
