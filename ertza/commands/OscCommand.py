# -*- coding: utf-8 -*-

from commands.AbstractCommands import AbstractCommand


class OscCommand(AbstractCommand):

    def execute(self, message):
        target, action, values = message.target, message.action, message.values
