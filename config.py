#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from base import BaseWorker

import time
import random

import configparser


class ConfigWorker(BaseWorker):
    """
    Master process that handle configuration.
    """

    def __init__(self, sm):
        super(ConfigWorker, self).__init__(sm)

        self.conf = self.sm.dict({'conf': 0})

        self.run()

    def run(self):
        while(self.running):
            self.conf['conf'] += 1
            self.mq.put(self.conf)
            time.sleep(random.random() / 10)


class ConfigProxy(object):
    """
    ConfigProxy provides an interface to a single ConfigParser instance.

    Helps sharing a simple config manager accross different processes.
    """

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


def log_worker(sm):
    mq = sm.queue
    cfpr = ConfigProxy()
    i = 0
    last_clock = 0
    inter_clock = 1
    while(True):
        if time.clock() >= last_clock + inter_clock:
            last_clock = time.time()
            print(cfpr.items())

        if not mq.empty():
            print(i, mq.get())
            i += 1
        time.sleep(0.01)


