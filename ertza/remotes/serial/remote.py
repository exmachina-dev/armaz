# -*- coding: utf-8 -*-

from collections import namedtuple

from ...errors import SerialError

import serial, bitstring

class RemoteControlLink(serial.Serial):
    product_keys = ('product_id', 'device_id', None, None)
    word_keys = namedtuple('WordKeys', ['ticks', 'turns', 'speed'])(0, 1, 2)
    command_keys = namedtuple('Command', ['ticks', 'turns', 'speed'])(
            'K', 'T', 'S')

    word_lenght = 48
    word_number = 3

    def __init__(self, port=None, baudrate=57600):
        super(RemoteControlLink, self).__init__(port=port, baudrate=baudrate)
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.timeout = None
        self.xonxoff = True

        self.product_infos = {}

    def _send_command(self, cmd, data=None):
        if not type(cmd) in (str, bytes):
            raise TypeError('Cmd must be a string or a byte')
        if len(cmd) != 1:
            raise ValueError('Cmd must be a string of lenght 1.')

        if type(cmd) is str:
            cmd.encode()

        if data:
            if type(data) is tuple and len(data) <= 4:
                d = bitstring.pack('>BBBB', *data)
            elif type(data) is int:
                d = bitstring.pack('>l', data)
            elif type(data) is float:
                d = bitstring.pack('>f', data)
            bits = bitstring.pack('bits', d)
        else:
            bits = bitstring.Bits()
        final_bytes = bitstring.pack(
                'uint:8, bits, uint:8',
                ord(cmd), bits, ord('\n'))
        print(bits)
        print(final_bytes.bin)
        return self.write(final_bytes.tobytes())

    def _serial_daemon(self):
        self.flushInput()
        if self.remote_mode == 'continuous':
            while not self.daemon_event.is_set():
                self.last_data = self.readline()
                self.daemon_event.wait(self.daemon_refresh)
        elif self.remote_mode == 'on_command':
            while not self.daemon_event.is_set():
                self.request_speed()
                self.request_ticks()
                self.request_turns()
                self.daemon_event.wait(self.daemon_refresh)

    def get_product_infos(self):
        self._send_command("R")
        r = self.readline()
        d = bitstring.Bits(bytes=r)
        print(d.bin, d.hex)
        if r[0] == ord('R'):
            d = bitstring.Bits(bytes=r[1:]).unpack('>BBBBB')
            for k, v in zip(self.product_keys, d):
                self.product_infos[k] = v
            return self.product_infos
        print(d)
        print(r)
        raise SerialError("Unexpected serial command")

    def get_speed(self):
        speed_c = self._get_data(self.word_keys.speed, 'float')
        self.last_speed = speed_c.float
        return self.last_speed

    def get_ticks(self):
        ticks_c = self._get_data(self.word_keys.ticks, 'long')
        self.last_ticks = ticks_c.long
        return self.last_ticks

    def get_turns(self):
        turns_c = self._get_data(self.word_keys.turns, 'float')
        self.last_turns = turns_c.float
        return self.last_turns

    def request_speed(self):
        raise NotImplementedError

    def request_ticks(self):
        raise NotImplementedError

    def request_turns(self):
        raise NotImplementedError

    def _get_data(self, word, data_type):
        offset = self.word_lenght * word

        if data_type == 'long':
            data_format = '>l'
        elif data_type == 'float':
            data_format = '>f'
        else:
            return False

        command = self.last_data[offset:offset+16]
        data = self.last_data[offset+16:offset+self.world_lenght]
        bits = bitstring.Bits(bytes=data).unpack(data_format)
        return bits




if __name__ == '__main__':
    test = input('Start serial test [y/N] ? ')
    if not test and test == 'y':
        default_device = '/dev/ttyUSB0'
        dev = input('Serial device [%s]: ' % default_device)
        if not dev:
            dev = default_device
        s = RemoteControlLink(dev)
        print('Product', s.get_product_infos())
        while True:
            print(s.get_ticks())
    else:
        s = RemoteControlLink()
