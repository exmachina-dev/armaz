#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import liblo as lo


global running
running = True

target = lo.Address(6069)


def sender(client, target):
    global running

    print('Sending to %s:%d' % (target.hostname, target.port))

    while running:
        osc_c = input("OSC command: ")
        if not osc_c:
            running = False
            sys.exit()

        try:
            path, args, = osc_c.split(' ')
            client.send(target, path, args)
        except ValueError:
            client.send(target, osc_c)


def server():
    port = 6070
    print('OSC server listening at %d' % port)
    srv = lo.ServerThread(port)
    return srv


@lo.make_method(None, None)
def callback(path, args, types, sender):
    if len(args) > 0:
        args = ' '.join(args)

    print('Got %s %s' % (path, args))

if __name__ == '__main__':
    trg = input('Target [127.0.0.1]: ')
    if trg:
        target = lo.Address(trg, 6069)

    running = True
    s = server()
    s.start()
    sender(s, target)
