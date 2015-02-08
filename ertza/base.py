# -*- coding: utf-8 -*-

import logging
import logging.handlers

class BaseWorker(object):
    """
    Base worker for multiprocessing.Manager()
    """

    interval = 0.5

    def __init__(self, sm):
        self.initializer = sm
        self.sm = sm.manager
        self.lgq = sm.log_queue
        self.cfpr = sm.configparser

        # Some events
        self.exit_event = sm.exit_event
        self.config_event = sm.config_event
        self.osc_event = sm.osc_event
        self.blockall_event = sm.blockall_event

        self.config_lock = sm.config_lock
        self.init_lock = sm.init_lock

        self.running = True

    def get_logger(self, name=__name__):
        _h = logging.handlers.QueueHandler(self.lgq) # Just the one handler needed
        self.lg = logging.getLogger(name)
        self.lg.addHandler(_h)
        self.lg.setLevel(logging.DEBUG)

    def run(self):
        pass
