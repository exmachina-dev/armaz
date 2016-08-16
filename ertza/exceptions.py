#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8
#
# Copyright © 2016 Benoit Rapidel <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the MIT license.

"""
Defines abstract exceptions.

This allow fine exception handling. Most submodules must subclass those
exceptions.
"""

from .led import Led


class AbstractErtzaException(Exception):
    def __init__(self, *args, **kwargs):
        delay = kwargs.pop('led_delay', 2000)
        Led.set_error_leds('flash', delay)
        super().__init__(*args, **kwargs)


class AbstractErtzaFatalException(AbstractErtzaException):
    def __init__(self, *args, **kwargs):
        delay = kwargs.pop('led_delay', 500)
        Led.set_error_leds('blink', delay)
        super().__init__(*args, **kwargs)
