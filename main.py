#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import multiprocessing as mp

from config import ConfigWorker
from config import ConfigProxy
from config import log_worker

import remote


class MainInitializer(object):
    """
    Main class

    Initialize all master processes such as remote, config and motor.
    Also initialize a log_worker for debug purposes.
    """

    manager = mp.Manager()
    queue = manager.Queue()
    config = manager.Namespace()

    configparser = ConfigProxy()
    configparser.read('default.conf')

    def __init__(self):
        self.jobs = []

    def processes(self):
        self.jobs = [
                mp.Process(target=ConfigWorker, name='armaz.cnf',
                    args=(self,)),
                mp.Process(target=remote.RemoteWorker, name='armaz.osc',
                    args=(self,)),
                mp.Process(target=log_worker, name='armaz.log',
                    args=(self,)),
                ]

    def start(self):
        for j in self.jobs:
            j.start()

    def join(self):
        for j in self.jobs:
            j.join()

if __name__ == "__main__":
    mi = MainInitializer()
    mi.processes()
    mi.start()
    mi.join()
