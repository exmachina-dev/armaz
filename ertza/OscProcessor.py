# -*- coding: utf-8 -*-

from Processor import Processor

from commands.OscCommand import OscCommand


class OscProcessor(Processor):

    def __init__(self, machine):
        super().__init__("commands.osc", OscCommand, machine)
