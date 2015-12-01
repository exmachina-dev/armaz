# -*- coding: utf-8 -*-

import sys
import logging

from drivers.Drivers import Driver


class Machine(object):

    def __init__(self):

        self.config = None
        self.driver = None

    def init_driver(self):
        drv = self.config.get('machine', 'driver', fallback=None)
        if drv is not None:
            try:
                self.driver = Driver().get_driver(drv)
                self.driver(self.config['driver_' + drv])
            except KeyError:
                logging.error("Unable to get %s driver, exiting." % drv)
                sys.exit()
        else:
            logging.error("Machine driver is not defined, aborting.")
            return False

        return drv
