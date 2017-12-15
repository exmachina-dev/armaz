#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
Provides abstract remote, a base remote
"""

from threading import Event
from queue import Queue


class AbstractRemote(object):
    """
    Represent a connected remote.
    """

    def __init__(self, *args, **kwargs):
        self.running_ev = Event()
        self.timeount_ev = Event()      # Timeout event when the remote doesn't respond

        self.messages_queue = Queue()

    def init_communication(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def handle(self, m):
        raise NotImplementedError

    @property
    def uid(self):
        raise NotImplementedError
