# -*- coding: utf-8 -*-

import sys
import logging

from drivers.Drivers import Driver


class Machine(object):

    def __init__(self):

        self.config = None
        self.driver = None

        self.comms = {}

    def init_driver(self):
        drv = self.config.get('machine', 'driver', fallback=None)
        if drv is not None:
            try:
                self.driver = Driver().get_driver(drv)(
                    self.config['driver_' + drv])
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
