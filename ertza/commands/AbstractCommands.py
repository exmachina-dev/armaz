# -*- coding: utf-8 -*-


class AbstractCommand(object):

    def __init__(self, machine):
        self.machine = machine
        self.eventReady = None

    def execute(self, command):
        raise NotImplementedError

    @property
    def alias(self):
        raise NotImplementedError

    @property
    def buffered(self):
        return False

    @property
    def synced(self):
        return False


class UnbufferedCommand(AbstractCommand):
    pass


class BufferedCommand(AbstractCommand):

    @property
    def buffered(self):
        return True


class SyncedCommand(AbstractCommand):

    @property
    def synced(self):
        return True
