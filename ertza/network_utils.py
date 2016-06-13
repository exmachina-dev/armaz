# -*- coding: utf-8 -*-

import subprocess


class IpAddress(object):
    def __init__(self, interface=None):
        self.interface = interface

        self.update_table()

    def update_table(self):
        c = ['ip', 'addr', 'show']
        if self.interface:
            c += ['dev', self.interface,]

        output = subprocess.check_output(c)
        r = [l.lstrip() for l in output.splitlines()]

        self._r = []
        for line in r:
            if not line.startswith(b'inet '):
                del line
            else:
                self._r.append(line.split()[1].decode())

    @property
    def ips(self):
        return self._r
