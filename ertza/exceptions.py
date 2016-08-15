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

class AbstractErtzaException(Exception):
    pass

class AbstractErtzaFatalException(AbstractErtzaException):
    pass
