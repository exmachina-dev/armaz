# -*- coding: utf-8 -*-

import logging

from ertza.commands import BufferedCommand
from ertza.commands import SerialCommand


class Identify(SerialCommand, BufferedCommand):

    def execute(self, c):
        infos = self.c.args + (self.c.data['serial_number'],)
        logging.info('Found %s %s with S/N %s' % infos)
        data = ('identify',) + self.machine.infos
        self.send(*data)

    @property
    def alias(self):
        return 'identify'
