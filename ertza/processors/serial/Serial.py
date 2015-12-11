# -*- coding: utf-8 -*-

import bitstring as bs
from collections import namedtuple


class SerialCommandString(object):
    CmdStruct = namedtuple('SerialCmd', ('protocol', 'serial_number', 'data', 'end'))
    CmdFormat = 'bits:64,bits:96,pad:32,bits,bits:16'
    CmdEnd = b'\r\n'
    CmdSep = b':'

    def __init__(self, cmd_bytes=None, **kwargs):
        if cmd_bytes:
            self._b = bs.pack(self.CmdFormat, cmd_bytes)
            self._c = self.CmdStruct(self._b.unpack())
        else:
            self._c = self.CmdStruct(b'', b'', b'', b'')
            self['serial_number'] = '000000000000'.encode()
            self['end'] = self.CmdEnd
            if 'protocol' in kwargs:
                self['protocol'] = kwargs['protocol']
            else:
                self['protocol'] = b'ExmEisla'

    @property
    def tobytes(self):
        return bs.pack(self.CmdFormat, *self._c)

    @property
    def command(self):
        return self['data'].split(self.CmdSep)[0]

    @property
    def args(self):
        return tuple(self['data'].decode().split(':')[1:])

    def __getitem__(self, key):
        return getattr(self._c, key)

    def __setitem__(self, key, value):
        if type(value) == str:
            value = value.encode()

        self._c = self._c._replace(**{key: value})

    def __add__(self, value):
        if type(value) == str:
            value = bs.Bits(value.encode())
        elif type(value) == int:
            value = bs.Bits(int=value, length=16)
        elif type(value) == float:
            value = bs.Bits(float=value, length=32)

        self['data'] += self.CmdSep + value
        return self

    def __len__(self):
        return self.tobytes.len

    def __repr__(self):
        return "%s %s %s" % (self['protocol'], self['serial_number'], self['data'])

    def __str__(self):
        return "%s %s %s" % (self['protocol'], self['serial_number'], self['data'])


class SerialTarget(object):
    def __init__(self, **kwargs):
        if 'unitid' in kwargs:
            self.unitid = kwargs['unitid']
        else:
            raise AttributeError('Missing arguments for creation.')

    def __repr__(self):
        return "%s" % self.unitid


class SerialMessage(object):

    def __init__(self, **kwargs):
        self.cmd_bytes = SerialCommandString(kwargs['cmd_bytes']) \
            if 'cmd_bytes' in kwargs else SerialCommandString()

        self.sender, self.receiver = None, None

        self.sender = SerialTarget(kwargs['sender']) if 'sender' in kwargs \
            else None
        self.receiver = SerialTarget(kwargs['receiver']) if 'receiver' in kwargs \
            else None

        self.msg_type = kwargs['msg_type'] if 'msg_type' in kwargs else None

        self.answer = None
        self.protocol = 'Serial'

    @property
    def command(self):
        return self.cmd_bytes.command

    @property
    def args(self):
        return self.cmd_bytes.args

    @property
    def tobytes(self):
        return self.cmd_bytes.tobytes

    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, self.cmd_bytes)
