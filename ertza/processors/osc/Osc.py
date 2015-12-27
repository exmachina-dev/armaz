# -*- coding: utf-8 -*-

from copy import copy
from liblo import Message


class OscPath(str):
    def __init__(self, path):
        self._p = path
        self.levels = self._p.split('/')

    def __repr__(self):
        return "%s" % '/'.join(self.levels)

    def __str__(self):
        return "%s" % '/'.join(self.levels)


class OscAddress(object):
    def __init__(self, address_object=None, **kwargs):
        if address_object:
            self.hostname = copy(address_object.hostname)
            self.port = int(copy(address_object.port))

            del(address_object)
        elif 'hostname' in kwargs:
            self.hostname = kwargs['hostname']

            if 'port' in kwargs:
                self.port = kwargs['port']
            else:
                self.port = 6970
        else:
            raise AttributeError('Missing arguments for creation.')

    def __repr__(self):
        return "%s:%d" % (self.hostname, self.port)


class OscMessage(object):

    def __init__(self, path, *args, **kwargs):
        self.path, self._args = OscPath(path), args
        self.sender, self.receiver = None, None
        self._args = [str(a) if isinstance(a, Exception) else a for a in self._args]

        if 'types' in kwargs:
            self.types = kwargs['types']

        self.sender = OscAddress(kwargs['sender']) if 'sender' in kwargs \
            else None
        self.receiver = OscAddress(kwargs['receiver']) if 'receiver' in kwargs \
            else None

        self.msg_type = kwargs['msg_type'] if 'msg_type' in kwargs else None

        self.answer = None
        self.protocol = 'OSC'

    @property
    def target(self):
        return repr(self.path)

    @property
    def action(self):
        return self.path.levels[-1]

    @property
    def args(self):
        return tuple(self._args)

    @property
    def message(self):
        return Message(self.path, *self.args)

    def __repr__(self):
        args = [str(i) for i in self.args]
        return '%s: %s %s' % (self.__class__.__name__, self.path,
                              ' '.join(args))
