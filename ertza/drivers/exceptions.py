# -*- coding: utf-8 -*-

from ..exceptions import AbstractErtzaException


class AbstractDriverError(AbstractErtzaException):
    def __init__(self, msg='', request=None, **kwargs):
        if request is not None:
            msg = msg + ' with {!s}'.format(request)

        AbstractErtzaException.__init__(self, msg, **kwargs)
        self.request = request


class AbstractDriverTimeoutError(AbstractDriverError):
    """
    Raised when a command times out.
    """
    pass
