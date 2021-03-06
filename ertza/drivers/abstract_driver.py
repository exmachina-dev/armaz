# -*- coding: utf-8 -*-


class AbstractDriver(object):

    def init_driver(self):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def exit(self):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError

    def get(self, *args, **kwargs):
        raise NotImplementedError

    def set(self, *args, **kwargs):
        raise NotImplementedError

    def __getitem__(self, key):
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __repr__(self):
        i = {
            'name': self.__class__.__name__,
            'target': None,
        }
        try:
            i['target'] = self.target
        except AttributeError:
            try:
                i['target'] = '{0.target_address!s}:{0.target_port}'.format(self)
            except AttributeError:
                pass
        return '{name}: {target!s}'.format(**i)

    __str__ = __repr__
