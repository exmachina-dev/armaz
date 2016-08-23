#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Benoit Rapidel <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
Exceptions for ertza.machine
"""

from threading import Event

from ..exceptions import AbstractErtzaException, AbstractErtzaFatalException


class AbstractMachineError(AbstractErtzaException):
    pass


class AbstractMachineTimeoutError(AbstractMachineError):
    timeout_event = Event()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.timeout_event:
            self.timeout_event.set()


class AbstractMachineFatalError(AbstractMachineError,
                                AbstractErtzaFatalException):
    fatal_event = Event()

    def __init__(self, *args, **kwargs):
        AbstractMachineError.__init__(self, *args, **kwargs)

        if self.fatal_event:
            self.fatal_event.set()

        AbstractErtzaFatalException.__init__(self, *args, **kwargs)


class MachineError(AbstractMachineError):
    pass


class MachineFatalError(AbstractMachineFatalError, MachineError):
    pass


class MachineTimeoutError(AbstractMachineTimeoutError, MachineError):
    pass


class SlaveMachineError(AbstractMachineError):
    def __init__(self, msg='', slave=None, **kwargs):
        if slave is not None:
            msg = msg + ' for {!s}'.format(slave)

        super().__init__(msg, **kwargs)
        self.slave = slave


class SlaveMachineFatalError(AbstractMachineFatalError, SlaveMachineError):
    pass


class SlaveMachineTimeoutError(AbstractMachineTimeoutError, SlaveMachineError):
    timeout_event = Event()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        SlaveMachineError.__init__(self, *args, **kwargs)

        if self.timeout_event:
            self.timeout_event.set()
