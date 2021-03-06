# -*- coding: utf-8 -*-


import importlib
import inspect
import logging

from threading import Event

from ..commands.abstract_commands import BufferedCommand
from ..commands.abstract_commands import SyncedCommand

from ..exceptions import AbstractErtzaException

logging = logging.getLogger('ertza.processors')


class ProcessorAliasError(AbstractErtzaException):
    pass


class AbstractProcessor(object):
    def __init__(self, base_module, abstract_class, outlet):
        self.base_module = base_module
        self.abstract_class = abstract_class
        self._outlet_coro = outlet

        self.commands = {}

    def start(self):
        self.outlet = self._outlet_coro(self.identifier)

        _module = importlib.import_module('ertza.{}'.format(self.base_module))
        self.load_classes_in_module(_module)

    def load_classes_in_module(self, module):
        for module_name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, self.abstract_class):
                try:
                    cmd = obj(self.outlet)
                    if not isinstance(cmd.alias, str):
                        logging.error('Bad command alias, expected str, '
                                      'found {}. Skipped command.'
                                      .format(type(cmd.alias)))
                        continue
                    self.commands[cmd.alias] = cmd
                except NotImplementedError:
                    # This is an abstract class, skip it
                    pass

    @property
    def available_commands(self):
        return self.commands

    def is_buffered(self, command):
        if isinstance(command, BufferedCommand):
            return True

        return False

    def is_synced(self, command):
        if isinstance(command, SyncedCommand):
            return True

        return False

    def synchronize(self, command):
        alias = self._check_in_commands(command)
        if alias:
            try:
                self.commands[alias].on_sync(command)
            except Exception as e:
                logging.error("Error while executing %s: %s", alias, e)
            return command

    def execute(self, command):
        try:
            alias = self._check_in_commands(command)
        except ProcessorAliasError as e:
            logging.error('{!s}'.format(e))
            raise
        try:
            if self.commands[alias].synced:
                self.commands[alias].readyEvent = Event()

            self.commands[alias].execute(command)

            if self.commands[alias].synced:
                self.commands[alias].readyEvent.wait()
        except Exception as e:
            import traceback
            logging.error('Error while executing {!s}: {!r}'.format(alias, e))
            traceback.print_exc(e)
        return command

    def enqueue(self, message):
        if self.is_buffered(message):
            self.machine.commands.send(message)
            if self.is_sync(message):
                self.machine.sync_commands.put(message)    # Yes, it goes into both queues!
        else:
            self.machine.unbuffered_commands.send(message)

    def _check_in_commands(self, message):
        alias = message.command
        if alias not in self.commands:
            raise ProcessorAliasError('Alias not found in '
                                      '{0.__class__.__name__}: {1}'
                                      .format(self, alias))

        return alias
