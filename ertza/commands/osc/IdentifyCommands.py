# -*- coding: utf-8 -*-

import logging

from ertza.commands.AbstractCommands import BufferedCommand
from ertza.commands.OscCommand import OscCommand


class Identify(OscCommand, BufferedCommand):

    def execute(self, c):
        infos = self.machine.infos + (self.machine.serialnumber,)
        self.ok(c, *infos)

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
