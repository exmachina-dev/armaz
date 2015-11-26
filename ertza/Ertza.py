#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Main class for ertza

import logging
import os
import os.path
import sys
import signal
from threading import Thread

from ConfigParser import ConfigParser
from Machine import Machine

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
    _DEFAULT_CONF = './conf/default.conf'
    main()
