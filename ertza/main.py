# -*- coding: utf-8 -*-

import multiprocessing as mp
import signal
import logging

from .config import ConfigWorker

from .utils import LogWorker

from .remotes import RemoteWorker
from .remotes import OSCWorker
from .remotes import ModbusWorker
from .remotes import SlaveWorker

from .errors import FatalError


class MainInitializer(object):
    """
    Main class

    Initialize all master processes such as remote, config and motor.
    Also initialize a LogWorker for debug purposes.
    """

    log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    manager = mp.Manager()
    log_queue = manager.Queue()

    cmd_args = None

    # Some events
    exit_event = manager.Event()
    blockall_event = manager.Event()
    cnf_ready_event = manager.Event()
    slv_ready_event = manager.Event()
    restart_osc_event = manager.Event()
    restart_rmt_event = manager.Event()
    restart_mdb_event = manager.Event()
    restart_slv_event = manager.Event()

    # Some locks
    config_lock = manager.Lock()
    init_lock = manager.Lock()

    # Config pipes
    cnf_log_pipe = mp.Pipe()
    cnf_rmt_pipe = mp.Pipe()
    cnf_osc_pipe = mp.Pipe()
    cnf_mdb_pipe = mp.Pipe()
    cnf_slv_pipe = mp.Pipe()

    mdb_osc_pipe = mp.Pipe()
    mdb_slv_pipe = mp.Pipe()
    mdb_rmt_pipe = mp.Pipe()
    slv_osc_pipe = mp.Pipe()
    slv_rmt_pipe = mp.Pipe()

    def __init__(self, args=None):
        self.jobs = []

        if args:
            self.cmd_args = args
            self.log.debug('Ertza started with %s', args)

    def processes(self):
        self.jobs = [
                mp.Process(target=LogWorker, name='ertza.log',
                    args=(self,)),
                mp.Process(target=ConfigWorker, name='ertza.cnf',
                    args=(self,)),
                mp.Process(target=RemoteWorker, name='ertza.rmt',
                    args=(self,)),
                mp.Process(target=OSCWorker, name='ertza.osc',
                    args=(self,)),
                mp.Process(target=ModbusWorker, name='ertza.mdb',
                    args=(self,)),
#                mp.Process(target=SlaveWorker, name='ertza.slv',
#                    args=(self,)),
                ]

    def start(self):
        self.log.debug('Starting processes')
        for j in self.jobs:
            j.start()

    def exit(self):
        self.exit_event.set()
        self.log.debug('Exiting')

    def join(self):
        for j in self.jobs:
            j.join()
        self.log_queue.put_nowait(None)

    def ignore_sigint(self):
        # Save a reference to the original signal handler for SIGINT.
        self._default_sigint = signal.getsignal(signal.SIGINT)

        # Set signal handling of SIGINT to ignore mode.
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def restore_sigint(self):
        # Since we spawned all the necessary processes already, 
        # restore default signal handling for the parent process. 
        signal.signal(signal.SIGINT, self._default_sigint)

    def main_run(self):
        self.ignore_sigint()
        self.processes()
        self.start()
        self.restore_sigint()

        try:
            signal.pause()
            self.join()
        except (KeyboardInterrupt, FatalError):
            print('Received keyboard interrupt, exiting...')

if __name__ == "__main__":

    mi = MainInitializer()
    mi.main_run()
