#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import liblo as lo


global running
running = True


def sender(client, target):
    global running

    print('Sending to %s:%d' % (target.hostname, target.port))

    last_command = None

    while running:
        osc_c = input("OSC command: ")
        if not osc_c:
            if last_command:
                path, args, = last_command.split(' ')
                client.send(target, path, args)

        try:
            path, args, = osc_c.split(' ')
            client.send(target, path, args)
            last_command = osc_c
        except ValueError:
            client.send(target, osc_c)


def server(port=6070):
    print('OSC server listening at %d' % port)
    srv = lo.ServerThread(port)
    return srv


@lo.make_method(None, None)
def callback(path, args, types, sender):
    if len(args) > 0:
        args = ' '.join(args)

    print('Got %s %s' % (path, args))

if __name__ == '__main__':
    trg = input('Target [127.0.0.1:6069]: ')
    trg = trg.split(':')

    if len(trg) == 2:
        target = lo.Address(trg[0], int(trg[1]))
    elif len(trg) == 1:
        target = lo.Address(trg[0], 6069)
    else:
        target = lo.Address(6069)

    listen_on = input('Listen on [6070]: ')
    running = True
    if listen_on:
        s = server(int(listen_on))
    else:
        s = server()

    s.start()
    sender(s, target)
