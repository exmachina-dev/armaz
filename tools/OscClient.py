#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import liblo as lo


global running
running = True

target = lo.Address(6069)


def sender(client):
    global running

    while running:
        osc_c = input("OSC command:")
        if not osc_c:
            running = False
            sys.exit()
        osc_c = osc_c.split(' ')
        try:
            client.send(target, osc_c[0], osc_c[1:])
        except ValueError:
            client.send(target, osc_c[0])


def server():
    port = 6070
    print('OSC server listening at %d' % port)
    srv = lo.ServerThread(port)
    srv.start()
    return srv


@lo.make_method(None, None)
def callback(path, args, types, sender):
    if len(args) > 0:
        args = ' '.join(args)

    print('Got %s %s' % (path, args))

if __name__ == '__main__':
    running = True
    s = server()
    sender(s)
