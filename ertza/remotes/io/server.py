# -*- coding: utf-8 -*-

import time
import subprocess

from ...config import ConfigRequest
from ...errors import RemoteError
from ..modbus import ModbusRequest

from .event_watcher import EventWatcher as SwitchHandler

SWITCH_PINS = (("GPIO0_30", 'switch_0', 112), ("GPIO0_31", 'switch_1', 113))


class RemoteServer(object):
    def __init__(self, config, **kwargs):
        self.fake_mode = False
        self._modbus, self.restart_event = None, None
        self._config = config

        if 'fake_mode' in kwargs:
            self.fake_mode = kwargs['fake_mode']

        if 'modbus' in kwargs:
            self._modbus = kwargs['modbus']
            self.mdb_request = ModbusRequest(self._modbus)

        if 'logger' in kwargs:
            self.lg = kwargs['logger']
        else:
            import logging
            self.lg = logging.getLogger()

        if 'restart_event' in kwargs:
            self.restart_event = kwargs['restart_event']

        self.config_request = ConfigRequest(self._config)

        self.switchs = list()
        self.switchs_actions = {}

        try:
            self.create_switch_pins()
        except (NameError, RuntimeError) as e:
            raise RemoteError(
                    'Error reading event, am I on a beaglebone ?',
                    self.lg) from e

    def run(self, interval=None, init=False):
        for s in self.switchs:
            s.wait_for_event()

    def create_switch_pins(self):
        if not self.fake_mode:
            SwitchHandler.callback = self.switch_callback
            SwitchHandler.inputdev = '/dev/input/event1'
            for p in SWITCH_PINS:
                a = self.config_request.get(p[1], 'action', None)
                r = self.config_request.get(p[1], 'reverse', False)
                self.switchs.append(SwitchHandler(*p, invert=r))
                self.switchs_actions[p[1]] = a
            self.switchs = tuple(self.switchs)
            return True
        return False

    def switch_callback(self, event):
        state = bool(event.state)
        if self.switchs_actions[event.name] == 'reverse':
            self.lg.info('Direction control: %s' % state)
            self.mdb_request.set_direction(state)
        elif self.switchs_actions[event.name] == 'activate':
            self.lg.info('RF Control: %s' % state)
            self.mdb_request.set_command(drive_enable=state)
