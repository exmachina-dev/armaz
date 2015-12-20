# -*- coding: utf-8 -*-

import logging
from collections import namedtuple

from ertza.Machine import Machine
from ertza.drivers.Drivers import Driver


Slave = namedtuple('Slave', ('serialnumber', 'address', 'driver', 'config'))


class SlaveMachine(Machine):

    def __init__(self, slave):

        self.config = slave.config
        self.driver = None

        self.slave = slave

    def init_driver(self):
        drv = self.slave.driver
        logging.info("Loading %s driver" % drv)
        if drv is not None:
            try:
                self.driver = Driver().get_driver(drv)(self.config)
            except KeyError:
                logging.error("Unable to get %s driver, aborting." % drv)
                return
        else:
            logging.error("Machine driver is not defined, aborting.")
            return False

        return drv

    def exit(self):
        self.driver.exit()

    @property
    def infos(self):
        rev = self.cape_infos['revision'] if self.cape_infos \
            else '0000'
        var = self.config.variant.split('.')

        return ('identify', var[0].upper(), var[1].upper(), rev)

    @property
    def serialnumber(self):
        return self.slave.serialnumber
