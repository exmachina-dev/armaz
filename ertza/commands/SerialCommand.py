# -*- coding: utf-8 -*-

from .AbstractCommands import AbstractCommand


class SerialCommand(AbstractCommand):
    @property
    def alias(self):
        # This fix a bug:
        # Processor seems to include this class while loading modules…
        return ':'

    def execute(self, message):
        target, action, args = message.target, message.action, message.args
