# -*- coding: utf-8 -*-

import sys
import logging

from drivers.Drivers import Driver


class Machine(object):

    def __init__(self):

        self.config = None
        self.driver = None

        self.comms = {}
        self.commands = None
        self.synced_commands = None
        self.unbuffered_commands = None

    def init_driver(self):
        drv = self.config.get('machine', 'driver', fallback=None)
        logging.info("Loading %s driver" % drv)
        if drv is not None:
            try:
                driver_config = self.config['driver_' + drv]
            except KeyError:
                driver_config = {}
                logging.error("Unable to get config for %s driver" % drv)

            try:
                self.driver = Driver().get_driver(drv)(driver_config)
            except KeyError:
                logging.error("Unable to get %s driver, exiting." % drv)
                sys.exit()
        else:
            logging.error("Machine driver is not defined, aborting.")
            return False

        return drv

    def start(self):

        self.driver.connect()

    def exit(self):

        del self.driver

    def reply(self, command):
        if command.answer is not None:
            self.send_message(command.protocol, command.answer)

    def send_message(self, protocol, msg):
        self.comms[protocol].send_message(msg)
