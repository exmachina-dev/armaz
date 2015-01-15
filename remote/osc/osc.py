#!/usr/bin python3
# -*- coding: utf-8 -*-

import liblo as lo

class OSCServer(lo.ServerThread):
    def __init__(self, config):
        self.config = config
        self.server_port = self.config.get('osc', 'server_port')
        self.client_port = self.config.get('osc', 'client_port')
        super(OSCServer, self).__init__(self.server_port, lo.UDP)
        self.ready = True

    def start(self):
        super(OSCServer, self).start()

    def send(self, dst, msg):
        super(OSCServer, self).send(lo.Address(dst.get_hostname(), self.client_port), msg)

    #def setConfig(self, c):
    #    for k, l in c:
    #        if k in ('feedback',):
    #            if k == 'feedback':
    #                self.feedback = bool(*l)

    #def getConfig(self):
    #    rtn = dict()
    #    rtn.update({'feedback', int(self.feedback), })

    #    return rtn

    #def heartbeat(self, destination, ok=True, src=None):
    #    if ok:
    #        state = '/ok'
    #    else:
    #        state = '/nok'
    #    if not src:
    #        src = 'mother'
    #    self.send(destination, '/heartbeat' + state + '/' + src)
