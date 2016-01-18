# -*- coding: utf-8 -*-


class Message(object):

    @property
    def command(self):
        raise NotImplementedError()

    @property
    def target(self):
        raise NotImplementedError()

    @property
    def args(self):
        raise NotImplementedError()
