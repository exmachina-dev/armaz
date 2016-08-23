# -*- coding: utf-8 -*-
"""
Declare exceptions used OscDriver.
"""

from threading import Event

from ..exceptions import AbstractDriverError, AbstractDriverTimeoutError


class OscDriverError(AbstractDriverError):
    pass


class OscDriverTimeout(OscDriverError, AbstractDriverTimeoutError):
    timeout_event = Event()
