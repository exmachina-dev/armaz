# -*- coding: utf-8 -*-

from ..exceptions import AbstractDriverError, AbstractDriverTimeoutError


class OscDriverError(AbstractDriverError):
    pass


class OscDriverTimeout(OscDriverError, AbstractDriverTimeoutError):
    pass
