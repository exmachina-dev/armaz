#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from base import BaseWorker

import time
import random

import configparser


class ConfigWorker(BaseWorker):
    def __init__(self, sm):
        super(ConfigWorker, self).__init__(sm)

        self.cfpr = ConfigProxy()
        self.cfpr.read('default.conf')

        self.conf = self.sm.dict({'conf': 0})

        self.run()

    def run(self):
        while(self.running):
            self.conf['conf'] += 1
            self.mq.put(self.conf)
            time.sleep(random.random() / 10)


class ConfigProxy(object):
    _obj = configparser.ConfigParser()

    def __getattribute__(self, name):
        return getattr(object.__getattribute__(self, "_obj"), name)

    def __delattr__(self, name):
        delattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_obj"), name, value)


    def __nonzero__(self):
        return bool(object.__getattribute__(self, "_obj"))

    def __str__(self):
        return str(object.__getattribute__(self, "_obj"))

    def __repr__(self):
        return repr(object.__getattribute__(self, "_obj"))

    #def __getitem__(self, key):
    #    return object.__getitem__(self, key)

    #def __delitem__(self, key):
    #    object.__delitem__(self, key)

    #def __setitem__(self, key, value):
    #    object.__setitem__(self, key, value)


def logWorker(sm):
    mq = sm.queue
    cf = sm.config
    i = 0
    while(True):
        if not mq.empty():
            print(i, mq.get())
            print(cf)
            i += 1


