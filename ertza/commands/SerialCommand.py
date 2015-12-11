# -*- coding: utf-8 -*-

from .AbstractCommands import AbstractCommand


class OscCommand(AbstractCommand):

    def execute(self, message):
        target, action, args = message.target, message.action, message.args
