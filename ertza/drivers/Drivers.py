# -*- coding: utf-8 -*-

from importlib import import_module


class Driver(object):
    def get_driver(self, driver):
        pkg = import_module("drivers.%s" % driver)
        return getattr(pkg, "%sDriver" % driver)
