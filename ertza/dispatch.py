#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Benoit Rapidel <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the MIT license.

"""
Communication dispatcher
"""

import logging

from .async_utils import coroutine
from .exceptions import AbstractErtzaException, AbstractErtzaFatalException

logging = logging.getLogger('ertza.dispatch')


class DispatcherException(AbstractErtzaException):
    pass


class DispatcherFatalException(AbstractErtzaFatalException):
    pass


class Dispatcher(object):
    """
    Communication dispatcher
    """
    def __init__(self, machine):
        self._machine = machine
        self._processors = {}
        self._servers = {}

    def add_server(self, server, name):
        if name in self._servers:
            raise DispatcherException('{} server already exists'.format(name))

        self._servers[name] = server

    def add_processor(self, proc, name):
        if name in self._servers:
            raise DispatcherException('{} processor already exists'.format(name))

        if name not in self._servers:
            raise DispatcherException('No server found for {}'.format(name))

        self._processors[name] = proc

    def start(self):
        for name, server in self._servers.items():
            logging.debug('Starting {} server'.format(name))
            server.start()
            logging.info('{} server started.'.format(name))

    @coroutine
    def inlet(self, name):
        try:
            proc = self._processors[name]
        except KeyError:
            raise DispatcherFatalError('Unable to find {} processor'.format(name))


