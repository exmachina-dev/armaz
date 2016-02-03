# -*- coding: utf-8 -*-

import logging
import liblo as lo
from threading import Thread

from .Osc import OscMessage

logging = logging.getLogger(__name__)


class OscServer(lo.Server):

    def __init__(self, machine):
        self.machine = machine
        self.processor = self.machine.processors['OSC']

        port = machine.config.getint('osc', 'listen_port', fallback=6969)
        self.reply_port = machine.config.getint('osc', 'reply_port',
                                                fallback=6969)

        super().__init__(port, lo.UDP)
        logging.info('Started OSC server on port %d' % port)

    def run(self):
        while self.running:
            self.recv(50)

    def start(self):
        self.running = True

        self._t = Thread(target=self.run)
        self._t.daemon = True
        self._t.start()

    def send_message(self, message):
        osc_msg = message.to_message()
        message.receiver.port = self.reply_port
        if message.msg_type is not 'log':
            logging.debug("Sending to %s: %s" % (message.receiver, message))
        self.send((message.receiver.hostname, self.reply_port), osc_msg)

    @lo.make_method(None, None)
    def dispatch(self, path, args, types, sender):
        m = OscMessage(path, *args, types=types, sender=sender)
        logging.debug('Received %s from %s' % (m, m.sender))
        self.processor.enqueue(m)

    def close(self):
        logging.debug('Closing OSC server')
        self.running = False
        self._t.join()

    exit = close


if __name__ == '__main__':

    import signal
    from multiprocessing import JoinableQueue

    from ...Machine import Machine
    from ...ConfigParser import ConfigParser
    from ..OscProcessor import OscProcessor

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
