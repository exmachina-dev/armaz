# -*- coding: utf-8 -*-

from copy import copy
from liblo import Message as OMessage

from ..abstract_message import AbstractMessage


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


class OscMessage(AbstractMessage):

    def __init__(self, path, *args, **kwargs):
        self.path, self._args = OscPath(path), args
        self.sender, self.receiver = None, None
        self._args = [str(a) if isinstance(a, Exception) else a for a in self._args]

        self.types = kwargs['types'] if 'types' in kwargs else None

        if self.types and len(self.types) != len(self._args):
            raise TypeError('Lenght of args and types must match')

        self.sender = OscAddress(kwargs['sender']) if 'sender' in kwargs \
            else None
        self.receiver = OscAddress(kwargs['receiver']) if 'receiver' in kwargs \
            else None

        if not (self.sender or self.receiver):
            self.receiver = OscAddress(**kwargs)

        self.msg_type = kwargs['msg_type'] if 'msg_type' in kwargs else None

        self.answer = None
        self.protocol = 'OSC'

    @property
    def command(self):
        return str(self.path)

    @property
    def target(self):
        return self.command.split('/')[0]

    @property
    def args(self):
        return tuple(self._args)

    def to_message(self):
        if self.types:
            a = []
            for i in zip(self.types, self.args):
                a.append(i)
            return OMessage(self.path, *a)
        return OMessage(self.path, *self.args)

    @property
    def message(self):
        return self.to_message()

    @property
    def uuid(self):
        uuid = self.args[0]
        return uuid

    uid = uuid

    def __repr__(self):
        args = [str(i) for i in self.args]
        return '%s: %s %s' % (self.__class__.__name__, self.path,
                              ' '.join(args))

    def __add__(self, value):
        self._args.append(value)
