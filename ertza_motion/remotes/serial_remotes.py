#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
OSC remotes
"""

from .abstract_remote import AbstractRemote
from ..processors.serial import SerialMessage


class SerialRemote(AbstractRemote):
    PROTOCOL = 'Serial'
    HAS_IP = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self):
        pass

    def handle(self, m):
        self.reply_ok(m)

    def reply_ok(self, msg, *args, **kwargs):
        self.reply(msg, *args, add_path='ok', **kwargs)

    def reply_error(self, msg, *args, **kwargs):
        self.reply(msg, *args, add_path='error', **kwargs)

    def reply(self, msg, *args, **kwargs):
        ap = kwargs.pop('add_path', None)
        if ap:
            if not isinstance(ap, str):
                raise TypeError('add_path kwarg must be a string')

            full_path = msg.command + ap \
                if ap.startswith(self.message.SEP) \
                else '{0.command}{0.message.SEP}{1}'.format(self, ap)
        else:
            full_path = self.command

        self.send(full_path, *args, **kwargs)

    def send(self, *args, **kwargs):
        msg = kwargs['msg'] if 'msg' in kwargs else \
            self.message()

        for d in args:
            msg.cmd_bytes += d

        return self.send_message(msg)

    def message(self, *args, **kwargs):
        return SerialMessage(*args, **kwargs)

    @property
    def uid(self):
        return self.__class__.__name__


class SerialVarmoRemote(SerialRemote):
    HAS_FEEDBACK = False
    REFRESH_INTERVAL = 1.0
