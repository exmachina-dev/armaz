# -*- coding: utf-8 -*-

from bitstring import BitString
from collections import namedtuple


class SerialCommandString(object):
    CmdStruct = namedtuple('SerialCmd', ('protocol', 'serial_number', 'data', 'end'))
    CmdFormat = 'bytes:8,bytes:12,pad:32,bytes,bytes:1'
    CmdEnd = b'\r\n'

    def __init__(self, cmd_bytes=None, **kwargs):
        if cmd_bytes:
            self._b = BitString(cmd_bytes, self.CmdFormat)
            self._c = self.CmdStruct(self._b.unpack())
        else:
            self._c = self.CmdStruct()
            self._c._replace(serial_number='0000')
            self._c._replace(end=self.CmdEnd)
            if 'protocol' in kwargs:
                self._c.protocol = kwargs['protocol']

    @property
    def tobytes(self):
        return BitString(self._c, self.CmdFormat).tobytes()

    def __getitem__(self, key):
        return self._c[key]

    def __setitem__(self, key, value):
        self._c._replace(**{key: value})

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

    def __init__(self, cmd_str, args, **kwargs):
        self.cmd_str, self._args = SerialCommandString(cmd_str), args
        self.sender, self.receiver = None, None

        self.sender = SerialTarget(kwargs['sender']) if 'sender' in kwargs \
            else None
        self.receiver = SerialTarget(kwargs['receiver']) if 'receiver' in kwargs \
            else None

        self.msg_type = kwargs['msg_type'] if 'msg_type' in kwargs else None

        self.answer = None
        self.protocol = 'Serial'

    @property
    def target(self):
        return repr(self.cmd_str)

    @property
    def action(self):
        pass

    @property
    def args(self):
        return self._args

    def tobytes(self):
        return self.cmd_str.tobytes

    def __repr__(self):
        return '%s: %s %s' % (self.__class__.__name__, self.path,
                              ' '.join(iter(self.args)))
