#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Benoit Rapidel <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the MIT license.

"""
Exceptions for ertza.machine
"""

from ..exceptions import AbstractErtzaException


class AbstractMachineError(AbstractErtzaException):
    pass


class AbstractMachineTimeoutError(AbstractMachineError):
    timeout_event = None

    def __init__(self, *args, **kwargs):
        AbstractMachineError.__init__(*args, **kwargs)

        if AbstractMachineTimeoutError.fatal_event:
            AbstractMachineTimeoutError.fatal_event.set()


class AbstractMachineFatalError(AbstractMachineError):
    fatal_event = None

    def __init__(self, *args, **kwargs):
        AbstractMachineError.__init__(*args, **kwargs)

        if AbstractMachineFatalError.fatal_event:
            AbstractMachineFatalError.fatal_event.set()


class MachineError(AbstractMachineError):
    pass


class MachineFatalError(AbstractMachineFatalError):
    pass


class MachineTimeoutError(MachineError):
    pass


class SlaveMachineError(AbstractMachineError):
    def __init__(self, msg='', slave=None, **kwargs):
        if slave is not None:
            msg = msg + ' for {!s}'.format(slave)

        AbstractMachineError.__init__(self, msg, **kwargs)
        self.slave = slave


class SlaveMachineFatalError(AbstractMachineFatalError, SlaveMachineError):
    pass


class SlaveMachineTimeoutError(SlaveMachineError):
    timeout_event = None

    def __init__(self, *args, **kwargs):
        SlaveMachineError.__init__(self, *args, **kwargs)

        if SlaveMachineTimeoutError.timeout_event:
            SlaveMachineTimeoutError.timeout_event.set()
