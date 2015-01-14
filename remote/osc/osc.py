#!/usr/bin python3
# -*- coding: utf-8 -*-

import liblo as lo

class OSCServer(lo.ServerThread):
    def __init__(self, config):
        self.config = config
        port = self.config['osc']['server_port']
        print(port)
        super(OSCServer, self).__init__(port, lo.UDP)
        self.config.clientPort = 7376
        self.ready = True

    def start(self):
        self.log.info('Osc thread starting.')
        super(OSCServer, self).start()

    def send(self, dst, msg):
        super(OSCServer, self).send(lo.Address(dst.get_hostname(), self.feedbackPort), msg)

    def setConfig(self, c):
        for k, l in c:
            if k in ('feedback',):
                if k == 'feedback':
                    self.feedback = bool(*l)

    def getConfig(self):
        rtn = dict()
        rtn.update({'feedback', int(self.feedback), })

        return rtn

    def heartbeat(self, destination, ok=True, src=None):
        if ok:
            state = '/ok'
        else:
            state = '/nok'
        if not src:
            src = 'mother'
        self.send(destination, '/heartbeat' + state + '/' + src)
