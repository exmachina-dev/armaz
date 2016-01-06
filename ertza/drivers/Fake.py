# -*- coding: utf-8 -*-

from .AbstractDriver import AbstractDriver


_FakeDict = {
    'serialnumber': '5315FKDV0001',
}


class FakeDriverError(Exception):
    pass


class FakeDriver(AbstractDriver):

    def __init__(self, config):
        if 'serialnumber' in config:
            _FakeDict['serialnumber'] = config['serialnumber']

        self.connected = False

    def connect(self):
        if not self.connected:
            self.connected = True

    def exit(self):
        pass

    def __getitem__(self, key):
        if key in _FakeDict.keys():
            return _FakeDict[key]
        raise KeyError
