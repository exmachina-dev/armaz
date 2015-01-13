#!/usr/bin/env python3

import multiprocessing as mp
import time
import random

class OscWorker(object):
    def __init__(self, sm, mq):
        self.sm = sm
        self.mq = mq
        self.running = True
        self.osc_commands = self.sm.dict({'cmd': 0})

        self.run()

    def run(self):
        while(self.running):
            self.osc_commands['cmd'] += 1
            self.mq.put(self.osc_commands)
            time.sleep(random.random() / 10)

class ConfWorker(object):
    def __init__(self, sm, mq):
        self.sm = sm
        self.mq = mq
        self.running = True
        self.conf = self.sm.dict({'conf': 0})

        self.run()

    def run(self):
        while(self.running):
            self.conf['conf'] += 1
            self.mq.put(self.conf)
            time.sleep(random.random() / 10)

def logWorker(sm, mq):
    i = 0
    while(True):
        if not mq.empty():
            print(i, mq.get())
            i += 1

def main():
    sm = mp.Manager()
    mq = sm.Queue()
    osc = mp.Process(target=OscWorker, name='armaz.osc', args=(sm, mq))
    conf = mp.Process(target=ConfWorker, name='armaz.cnf', args=(sm, mq))
    log = mp.Process(target=logWorker, name='armaz.log', args=(sm, mq))

    jobs = [
            osc,
            conf,
            log
            ]

    for j in jobs:
        j.start()
    for j in jobs:
        j.join()
        
    print('Done')

if __name__ == "__main__":
    main()
