# -*- coding: utf-8 -*-

import logging

from ertza.commands.AbstractCommands import BufferedCommand
from ertza.commands.SerialCommand import SerialCommand


class Identify(SerialCommand, BufferedCommand):

    def execute(self, c):
        infos = self.c.args + (self.c.data['serial_number'],)
        logging.info('Found %s %s with S/N %s' % infos)
        rev = self.machine.cape_infos['revision'] if self.machine.cape_infos \
            else '0000'
        data = ('identify', 'Armaz', self.machine.config.variant, rev)
        self.send(*data)

    @property
    def alias(self):
        return 'identify'
