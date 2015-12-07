# -*- coding: utf-8 -*-

from drivers.AbstractDriver import AbstractDriver


class FakeDriverError(Exception):
    pass


class FakeDriver(AbstractDriver):

    def __init__(self, config):
        self.connected = False

    def connect(self):
        if not self.connected:
            self.connected = True
