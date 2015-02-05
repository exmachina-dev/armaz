# -*- coding: utf-8 -*-

import multiprocessing as mp

from ertza.config import ConfigWorker
from ertza.config import ConfigProxy
from ertza.utils import LogWorker

from ertza.remotes import RemoteWorker


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
    #configparser.read_configs('default.conf')

    # Some events
    exit_event = manager.Event()
    config_event = manager.Event()
    blockall_event = manager.Event()

    # Some locks
    config_lock = manager.Lock()
    init_lock = manager.Lock()

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
