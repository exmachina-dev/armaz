# -*- coding: utf-8 -*-

import logging
import logging.handlers

class BaseWorker(object):
    """
    Base worker for multiprocessing.Manager()
    """

    def __init__(self, sm):
        self.initializer = sm
        self.sm = sm.manager
        self.lgq = sm.log_queue
        self.cf = sm.config
        self.cfpr = sm.configparser

        self.running = True

    def get_logger(self):
        _h = logging.handlers.QueueHandler(self.lgq) # Just the one handler needed
        self.lg = logging.getLogger(__name__)
        self.lg.addHandler(_h)
        self.lg.setLevel(logging.DEBUG)

    def run(self):
        pass
