# -*- coding: utf-8 -*-

import logging
import serial as sr
from threading import Thread

from .Serial import SerialMessage, SerialCommandString


class SerialServer(sr.Serial):

    def __init__(self, machine):
        self.machine = machine
        self.processor = self.machine.serial_processor

        dev = machine.config.get('serial', 'listen_device')
        if dev == 'None':
            dev = None
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
                data = self.read(self.inWaiting() or 1)
                if data:
                    self.data_buffer += (data)
                    self.find_serial_packets()
        except sr.SerialException as e:
            logging.error(e)
        except:
            pass

    def start(self):
        self.running = True

        self._t = Thread(target=self.run)
        self._t.start()

        m = SerialMessage()
        m.cmd_bytes['data'] = 'alive'
        self.send_message(m)

    def send_message(self, message):
        if message.msg_type is not 'log':
            logging.debug("Sending: %s %s" % (message, message.tobytes))
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
