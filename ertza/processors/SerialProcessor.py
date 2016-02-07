# -*- coding: utf-8 -*-

import logging

from .Processor import Processor

from ..commands.SerialCommand import SerialCommand

logging = logging.getLogger(__name__)


class SerialProcessor(Processor):

    def __init__(self, machine):
        super().__init__("commands.serial", SerialCommand, machine)

        serial_cmds = ' '.join(self.available_commands)
        logging.info("Serial commands loaded: %s" % serial_cmds)
