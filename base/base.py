#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class BaseWorker(object):
    def __init__(self, sm):
        self.initializer = sm
        self.sm = sm.manager
        self.mq = sm.queue
        self.cf = sm.config
        self.cfpr = sm.configparser

        self.running = True

    def run(self):
        pass
