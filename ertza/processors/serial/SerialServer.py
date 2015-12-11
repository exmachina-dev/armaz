# -*- coding: utf-8 -*-

import logging
import serial as sr
from threading import Thread

from .Serial import SerialMessage, SerialCommandString


class SerialServer(sr.Serial):

    def __init__(self, machine):
        self.machine = machine
        self.processor = self.machine.serial_processor

        dev = machine.config.getint('serial', 'listen_device')
        baudrate = machine.config.getint('serial', 'baudrate', fallback=57600)

        super().__init__(port=dev, baudrate=baudrate)

        self.bytesize = sr.EIGHTBITS
        self.parity = sr.PARITY_NONE
        self.stopbits = sr.STOPBITS_ONE
        self.timeout = 0.05
        self.xonxoff = False

        self.data_buffer = b''

    def run(self):
        try:
            while self.running:
                # read all that is there or wait for one byte
                data = self.read(self.in_waiting or 1)
                if data:
                    self.data_buffer += (data)
                    self.find_serial_packets()
        except sr.SerialException as e:
            logging.error(e)

    def start(self):
        self.running = True

        self._t = Thread(target=self.run)
        self._t.start()

        m = SerialMessage()
        m.cmd_bytes['data'] = 'alive'
        self.send_message(m)

    def send_message(self, message):
        if message.msg_type is not 'log':
            logging.debug("Sending to %s: %s" % (message.receiver, message))
        self.write(message.tobytes)

    def close(self):
        self.running = False
        self._t.join()

    def find_serial_packets(self):
        pos = self.data_buffer.lfind(SerialCommandString.CmdEnd)
        if pos >= 0:
            packet, self.data_buffer = self.data_buffer[:pos+2], \
                self.data_buffer[pos+2:]
            m = SerialMessage(packet)
            self.machine.serial_processor.enqueue(m, self.processor)
            self.find_serial_packets()


if __name__ == '__main__':

    import signal
    from multiprocessing import JoinableQueue

    from ...Machine import Machine
    from ...ConfigParser import ConfigParser
    from ..SerialProcessor import SerialProcessor

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

    m.serial_processor = SerialProcessor(m)
    s = SerialServer(m)
    s.start()

    signal.pause()
