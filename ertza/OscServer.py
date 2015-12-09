# -*- coding: utf-8 -*-

import logging
import liblo as lo
from threading import Thread

from .Osc import OscMessage


class OscServer(lo.Server):

    def __init__(self, machine):
        self.machine = machine
        self.processor = self.machine.osc_processor

        port = machine.config.getint('osc', 'port', fallback=6069)

        super().__init__(port, lo.UDP)

    def run(self):
        while self.running:
            self.recv(1)

    def start(self):
        self.running = True

        self._t = Thread(target=self.run)
        self._t.start()

    def send_message(self, message):
        osc_msg = lo.Message(message.path, *message.args)
        logging.debug("Sending to %s: %s" % (message.receiver, message))
        self.send((message.receiver.hostname, 6970), osc_msg)

    @lo.make_method(None, None)
    def dispatch(self, path, args, types, sender):
        m = OscMessage(path, args, types=types, sender=sender)
        logging.debug('Received %s' % m)
        self.machine.osc_processor.enqueue(m, self.processor)

    def close(self):
        self.running = False
        self._t.join()


if __name__ == '__main__':

    import signal
    from multiprocessing import JoinableQueue

    from Machine import Machine
    from ConfigParser import ConfigParser
    from OscProcessor import OscProcessor

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s \
                        %(levelname)-8s %(message)s',
                        datefmt='%Y/%m/%d %H:%M:%S')

    m = Machine()
    c = ConfigParser('../conf/default.conf')

    m.config = c
    m.commands = JoinableQueue(10)
    m.unbuffered_commands = JoinableQueue(10)
    m.synced_commands = JoinableQueue()

    m.osc_processor = OscProcessor(m)
    o = OscServer(m)
    o.start()

    signal.pause()
