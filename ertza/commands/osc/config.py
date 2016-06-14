# -*- coding: utf-8 -*-

import logging

from ertza.commands import UnbufferedCommand
from ertza.commands import OscCommand


class ConfigSet(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if len(c.args) < 3:
            self.send(c.sender, '/config/error',
                      'Missing arguments for %s (%d)' % (self.alias, len(c.args)))
            return
        sec, opt, val, = c.args
        self.send(c.sender, '/config/info',
                  'Setting [%s] %s to %s' % (sec, opt, val))

        try:
            self.machine.config.set(sec, opt, val)
            logging.info('[%s] %s set to %s by %s' % (sec, opt, val, c.sender))
        except:
            self.send(c.sender, '/config/error',
                      'Unable to set [%s] %s to %s' % (sec, opt, val))

    @property
    def alias(self):
        return '/config/set'


class ConfigGet(OscCommand, UnbufferedCommand):

    def execute(self, c):
        if len(c.args) != 2:
            self.send(c.sender, '/config/error',
                      'Invalid number of arguments for %s' % self.alias,)
            return
        sec, opt = c.args

        try:
            val = self.machine.config.get(sec, opt)
            self.send(c.sender, '/config/get/%s/%s' % (sec, opt), val)
        except:
            self.send(c.sender, '/config/error',
                      'Unable to get [%s] %s' % (sec, opt))

    @property
    def alias(self):
        return '/config/get'


class ConfigSave(OscCommand, UnbufferedCommand):

    def execute(self, c):
        try:
            self.machine.config.save()
            self.ok(c)
        except Exception as e:
            self.error(c, repr(e))

    @property
    def alias(self):
        return '/config/save'
