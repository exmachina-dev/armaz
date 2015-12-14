# -*- coding: utf-8 -*-

import logging

from ertza.commands.AbstractCommands import BufferedCommand
from ertza.commands.OscCommand import OscCommand


class Identify(OscCommand, BufferedCommand):

    def execute(self, c):
        infos = self.c.args + (self.c.data['serial_number'],)
        logging.info('Found %s %s with S/N %s' % infos)
        self.ok(self.machine.infos)

    @property
    def alias(self):
        return '/identify'
