# -*- coding: utf-8 -*-

from ertza.commands import BufferedCommand
from ertza.commands import OscCommand


class Identify(OscCommand, BufferedCommand):

    def execute(self, c):
        self.ok(c, self.machine.serialnumber, self.machine.address)

    @property
    def alias(self):
        return '/identify'


class Version(OscCommand, BufferedCommand):

    def execute(self, c):
        version = self.machine.version
        self.ok(c, version)

    @property
    def alias(self):
        return '/version'
