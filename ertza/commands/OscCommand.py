# -*- coding: utf-8 -*-

from commands.AbstractCommands import AbstractCommand


class OscCommand(AbstractCommand):

    @property
    def alias(self):
        return '/'

    def execute(self, message):
        target, action, args = message.target, message.action, message.args
