# -*- coding: utf-8 -*-


class OscMessage(object):

    def __init__(self, path, args, types, sender):
        self.path, self.args, self.types = path, args, types
        self.sender = sender

    @property
    def target(self):
        return self.path.split('/')[0:-2]

    @property
    def action(self):
        return self.path.split('/')[-1]

    def values(self):
        for a in self.args:
            yield a
