# -*- coding: utf-8 -*-

from ..abstract_driver import AbstractDriverError, AbstractTimeoutError


class OscDriverError(AbstractDriverError):
    pass


class OscDriverTimeout(OscDriverError, AbstractTimeoutError):
    pass
