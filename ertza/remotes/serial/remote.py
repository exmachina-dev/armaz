# -*- coding: utf-8 -*-

from ...errors import SerialError

import serial, bitstring

class RemoteControlLink(serial.Serial):
    product_keys = ['product_id', 'device_id', None, None]
    def __init__(self, port=None, baudrate=57600):
        super(RemoteControlLink, self).__init__(port=port, baudrate=baudrate)
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.timeout = None
        self.xonxoff = True

        self.flushInput()

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

    def get_product_infos(self):
        self._send_command("R")
        r = self.readline()
        d = bitstring.Bits(bytes=r)
        print(d.bin, d.hex)
        if r[0] == ord('R'):
            d = bitstring.Bits(bytes=r[1:]).unpack('>BBBB')
            for k, v in zip(self.product_keys, d):
                self.product_infos[k] = v
            return self.product_infos
        return None

    def get_speed(self):
        print(1)
        self._send_command("S")
        r = self.readline()
        d = bitstring.Bits(bytes=r)
        print(d.bin, d.hex)
        if r[0] == ord('S'):
            d = bitstring.Bits(bytes=r[1:]).unpack('>f')
            self.speed = d.float
            return self.speed
        return None

    def get_ticks(self):
        self._send_command("T")
        r = self.readline()
        d = bitstring.Bits(bytes=r)
        print(d.bin, d.hex)
        if r[0] == ord('T'):
            d = bitstring.Bits(bytes=r[1:]).unpack('>l')
            self.ticks = d.long
            return self.ticks
        return None


if __name__ == '__main__':
    s = RemoteControlLink('/dev/ttyO1')
    s.get_product_id()
