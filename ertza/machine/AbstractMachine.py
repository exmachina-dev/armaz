# -*- coding: utf-8 -*-


class AbstractMachineError(Exception):
    pass


class AbstractFatalMachineError(AbstractMachineError):
    pass


class AbstractMachine(object):

    def __init__(self):
        self.version = None

        self.config = None
        self.driver = None

    def init_driver(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def exit(self):
        raise NotImplementedError

    def reply(self, command):
        raise NotImplementedError

    def send_message(self, msg):
        raise NotImplementedError

    @property
    def infos(self):
        raise NotImplementedError

    @property
    def serialnumber(self):
        raise NotImplementedError

    @property
    def address(self):
        raise NotImplementedError
