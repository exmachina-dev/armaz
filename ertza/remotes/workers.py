# -*- coding: utf-8 -*-

from ertza.base import BaseWorker
from ertza.remotes.osc import OSCServer

import time

class RemoteWorker(BaseWorker):
    """
    Master process that handle all communication instances:
        - OSCServer
        - Discret I/Os
        - Accessories serial bus
        - LCD display
    """

    def __init__(self, sm):
        super(RemoteWorker, self).__init__(sm)
        self.get_logger()
        self.lg.debug("Init of RemoteWorker")

        while not self.config_event.is_set():
            self.lg.debug('Waiting for config…')
            time.sleep(0.1)

        self.run()

    def run(self):
        try:
            self.start_osc_server()
        except SystemError as e:
            self.lg.warn(e)
            self.exit_event.set()

        while not self.exit_event.is_set():
            if self.osc_event.is_set():
                self.start_osc_server(True)
                self.osc_event.clear()

            time.sleep(0.5)

    def start_osc_server(self, restart=False):
        if restart:
            del self.osc_server
        self.osc_server = OSCServer(self.cfpr, self.lg, self.osc_event)
        self.osc_server.start()


__all__ = ['RemoteWorker']
