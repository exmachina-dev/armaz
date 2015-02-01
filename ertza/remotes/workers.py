# -*- coding: utf-8 -*-

from ertza.base import BaseWorker
from ertza.remotes.osc import OSCServer

import time
import random

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
        self.lg.debug("Init of RemoteWorker")

        self.running_for = 0

        self.osc_server = OSCServer(self.cfpr, self.lg)

        self.run()

    def run(self):
        self.osc_server.start()
        while(self.running):
            #self.running_for += 1
            #self.mq.put(self.running_for)
            #self.mq.put(self.cfpr.get('osc', 'server_port'))
            time.sleep(1)

__all__ = ['RemoteWorker']
