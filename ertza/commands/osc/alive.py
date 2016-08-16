# -*- coding: utf-8 -*-

import logging

from ertza.commands import UnbufferedCommand
from ertza.commands import OscCommand

logging = logging.getLogger('ertza.commands.osc')


class AliveResp(OscCommand, UnbufferedCommand):
    def execute(self, c):
        if not self.check_args(c, 'eq', 2, reply=False):
            logging.debug('Bad alive request received, ignoring.')
            return

        new_sn, new_ip = c.args
        if new_sn is None:
            # Don't register if S/N is empty
            return

        if new_ip == self.machine.osc_address:
            # Don't register ourselves
            return

        self.machine.alive_machines[new_sn] = new_ip

    @property
    def alias(self):
        return '/alive'
