#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from base import BaseWorker
from config import ConfigProxy
from .osc import OSCServer

import time
import random

class RemoteWorker(BaseWorker):
    def __init__(self, sm):
        super(RemoteWorker, self).__init__(sm)

        self.cfpr = ConfigProxy()
        self.osc_server = OSCServer(self.cfpr)

        self.run()

    def run(self):
        while(self.running):
            self.osc_commands['cmd'] += 1
            self.cf.osc = self.osc_commands['cmd']
            self.mq.put(self.osc_commands)
            time.sleep(random.random() / 10)


