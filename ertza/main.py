# -*- coding: utf-8 -*-

import multiprocessing as mp

from .config import ConfigWorker
from .config import ConfigProxy
from .config import LogWorker


class MainInitializer(object):
    """
    Main class

    Initialize all master processes such as remote, config and motor.
    Also initialize a LogWorker for debug purposes.
    """

    manager = mp.Manager()
    log_queue = manager.Queue()
    config = manager.Namespace()

    configparser = ConfigProxy()
    configparser.read('default.conf')

    def __init__(self):
        self.jobs = []

    def processes(self):
        self.jobs = [
                mp.Process(target=ConfigWorker, name='ertza.cnf',
                    args=(self,)),
                mp.Process(target=RemoteWorker, name='ertza.rmt',
                    args=(self,)),
                mp.Process(target=LogWorker, name='ertza.log',
                    args=(self,)),
                ]

    def start(self):
        for j in self.jobs:
            j.start()

    def join(self):
        for j in self.jobs:
            j.join()
        self.log_queue.put_nowait(None)

if __name__ == "__main__":
    mi = MainInitializer()
    mi.processes()
    mi.start()
    mi.join()
