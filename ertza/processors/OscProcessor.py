# -*- coding: utf-8 -*-

import logging

from .Processor import Processor

from ..commands.OscCommand import OscCommand


class OscProcessor(Processor):

    def __init__(self, machine):
        super().__init__("commands.osc", OscCommand, machine)

        osc_cmds = ' '.join(self.available_commands)
        logging.info("OSC commands loaded: %s" % osc_cmds)
