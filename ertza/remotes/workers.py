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

        self.osc_server = OSCServer(self.cfpr, self.lg)

        while not self.config_lock.is_set():
            self.lg.debug('Waiting for config…')
            time.sleep(0.1)

        self.run()

    def run(self):
        try:
            self.osc_server.start()
        except SystemError as e:
            self.lg.warn(e)
            self.exit_event.set()

        while not self.exit_event.is_set():
            #self.running_for += 1
            #self.mq.put(self.running_for)
            #self.mq.put(self.cfpr.get('osc', 'server_port'))
            time.sleep(0.5)

__all__ = ['RemoteWorker']
