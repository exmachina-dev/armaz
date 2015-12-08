# -*- coding: utf-8 -*-

from copy import copy


class OscPath(str):
    def __init__(self, path):
        self._p = path
        self.levels = self._p.split('/')

    def __repr__(self):
        return "%s" % '/'.join(self.levels)

    def __str__(self):
        return "%s" % '/'.join(self.levels)


class OscAddress(object):
    def __init__(self, address_object):
        self.hostname = copy(address_object.hostname)
        self.port = int(copy(address_object.port))

        del(address_object)

    def __repr__(self):
        return "%s:%d" % (self.hostname, self.port)


class OscMessage(object):

    def __init__(self, path, args, **kwargs):
        self.path, self._args = OscPath(path), args
        self.sender, self.receiver = None, None

        if 'types' in kwargs:
            self.types = kwargs['types']

        if 'sender' in kwargs:
            self.sender = OscAddress(kwargs['sender'])
        if 'receiver' in kwargs:
            self.receiver = OscAddress(kwargs['receiver'])

        self.answer = None
        self.protocol = 'OSC'

    @property
    def target(self):
        return self.path.split('/')[0:-2]

    @property
    def action(self):
        return self.path.split('/')[-1]

    @property
    def args(self):
        for a in self._args:
            yield a

    def __repr__(self):
        return '%s: %s %s' % (self.__class__.__name__, self.path,
                              ' '.join(iter(self.args)))
