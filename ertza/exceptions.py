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

__all__ = ['AbstractErtzaException', 'AbstractErtzaFatalException']


class _ErtzaException(Exception):
    def __init__(self, msg=''):
        self.message = msg
        Exception.__init__(self, msg)

    def __repr__(self):
        return '{0.__class__.__name__}({0.message})'.format(self)

    def __str__(self):
        return self.message


class AbstractErtzaException(_ErtzaException):
    def __init__(self, *args, **kwargs):
        delay = kwargs.pop('led_delay', 2000)
        Led.set_error_leds('flash', delay)
        super().__init__(*args, **kwargs)


class AbstractErtzaFatalException(AbstractErtzaException):
    def __init__(self, *args, **kwargs):
        delay = kwargs.pop('led_delay', 500)
        Led.set_error_leds('blink', delay)
        super().__init__(*args, **kwargs)
