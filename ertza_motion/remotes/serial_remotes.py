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


class SerialRemote(AbstractRemote):
    PROTOCOL = 'Serial'
    HAS_IP = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self):
        pass

    def handle(self, m):
        print(m)

    @property
    def uid(self):
        return self.__class__.__name__


class SerialVarmoRemote(SerialRemote):
    HAS_FEEDBACK = False
    REFRESH_INTERVAL = 1.0
