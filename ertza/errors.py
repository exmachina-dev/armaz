# -*- coding: utf:8 -*-
import sys

class ErtzaError(Exception):
    """Base class for Ertza exceptions."""

    def __init__(self, msg='', lg=None):
        self.message = msg
        Exception.__init__(self, msg)
        if lg:
            lg.warn(msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class FatalError(ErtzaError):
    """Raised when program cannot continue."""

    def __init__(self, msg='', lg=None):
        msg = 'Fatal: %s' % (msg,)
        ErtzaError.__init__(self, msg)
        if lg:
            lg.error(msg)


class TimeoutError(ErtzaError):
    """Raised on a function timeout."""

    def __init__(self, msg='', lg=None):
        ErtzaError.__init__(self, 'Timeout: %s' % (msg,), lg)


class ConfigError(FatalError):
    """Raised when program cannot load config."""

    def __init__(self, msg='', lg=None):
        FatalError.__init__(self, 'Unable to load config: %s' % (msg,), lg)


class RemoteError(ErtzaError):
    """Raised in remote server."""

    def __init__(self, msg='', lg=None):
        ErtzaError.__init__(self, 'Remote server: %s' % (msg,), lg)


class RemoteServerError(FatalError, RemoteError):
    """Raised when program cannot start remotes server."""

    def __init__(self, msg='', lg=None):
        FatalError.__init__(self, 'Cannot start Remote server: %s' % (msg,), lg)


class OSCServerError(FatalError):
    """Raised when program cannot start OSC server."""

    def __init__(self, msg='', lg=None):
        FatalError.__init__(self, 'Cannot start OSC server: %s' % (msg,), lg)


class SlaveError(FatalError):
    """Raised in Slave server."""

    def __init__(self, msg='', lg=None):
        FatalError.__init__(self, 'Slave error: %s' % (msg,), lg)


class SerialError(FatalError):
    """Raised when program cannot start OSC server."""

    def __init__(self, msg='', lg=None):
        FatalError.__init__(self, 'Serial error: %s' % (msg,), lg)


class ModbusMasterError(ErtzaError):
    """Raised in Modbus master."""

    def __init__(self, msg='', lg=None):
        ErtzaError.__init__(self, 'Modbus master: %s' % (msg,), lg)
