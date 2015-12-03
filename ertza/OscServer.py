# -*- coding: utf-8 -*-

import liblo as lo
from threading import Thread

from Osc import OscMessage


class OscServer(lo.Server):

    def __init__(self, machine):
        self.machine = machine
        self.port = machine.config.getint('osc', 'port')

        super().__init__(self.port, lo.UDP)

    def run(self):
        while self.running:
            self.recv(1)

    def start(self):
        self.running = True

        self._t = Thread(target=self.run)
        self._t.start()

    @lo.make_method(None, None)
    def dispatch(self, path, args, types, sender):
        m = OscMessage(path, args, types, sender)
        self.machine.osc_processor.enqueue(m)

    def close(self):
        self.running = False
        self._t.join()
