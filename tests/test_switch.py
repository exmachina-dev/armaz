# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Benoit Rapidel <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the MIT license.


import pytest

import os
import logging
from threading import Event
import struct
import time
import socket

from ertza.switch import Switch as _Switch
from ertza.switch import EventTypes, SwitchException, InputEvent

logging.basicConfig()
logger = logging.getLogger('ertza')
logger.setLevel(10)


class MockSwitch(_Switch):
    _socket = None

    @classmethod
    def _wait_for_events(cls):
        try:
            with cls._socket as evt_file:
                while not cls._running_event.is_set():
                    evt = cls._get_event(evt_file)

                    if evt is None:
                        continue

                    cls._process_event(evt)
        except OSError as e:
            logging.error('Unable to access to inputdev file: {!s}'.format(e))
            raise SwitchException(str(e))

    @classmethod
    def _get_event(self, sock):
        ev_data = sock.recv(16)

        if len(ev_data) == 16:
            return InputEvent(ev_data)


Switch = MockSwitch


class Test_Switch(object):
    def _write_to_inputdev(self, key, hit):
        ev = struct.pack('<dHHHH', 0, EventTypes.SW, key, hit, 0)
        ev += b'\x00' * 16


        self.sock.send(ev)

    def setup_class(self):
        self.inputdev = os.path.realpath('./tests/inputdev')
        self.sock, sw_sock = socket.socketpair()
        self.data_ev = Event()
        self.wait_ev = Event()
        self.rtn_data = {}

        def _cb(sw_state):
            self.wait_ev.wait()
            logger.info('Write')

            self.rtn_data = sw_state.copy()

            self.data_ev.set()

        Switch.callback = _cb
        Switch._inputdev = True
        Switch._socket = sw_sock

    def test_non_existing_inpudev_file(self):
        with pytest.raises(FileNotFoundError):
            _Switch.set_inputdev('./tests/nonexisting_dir')

    def test_switch(self):
        self.wait_ev.clear()
        self.data_ev.clear()

        Switch.start()
        Switch(115, 'test115')
        Switch(116, 'test116')
        Switch(117, 'test117', invert=True)

        self._write_to_inputdev(115, True)
        self.wait_ev.set()
        self.data_ev.wait()
        st = dict(self.rtn_data)
        assert st['keycode'] == 115
        assert st['name'] == 'test115'
        assert st['direction'] == True
        assert st['hit'] == True

        self.wait_ev.clear()
        self.data_ev.clear()
        self._write_to_inputdev(116, True)
        self.wait_ev.set()
        self.data_ev.wait(1)
        st = dict(self.rtn_data)
        assert st['keycode'] == 116
        assert st['name'] == 'test116'
        assert st['direction'] == True
        assert st['hit'] == True
        assert st['invert'] == False

        self.wait_ev.clear()
        self.data_ev.clear()
        self._write_to_inputdev(117, True)
        self.wait_ev.set()
        self.data_ev.wait()
        st = dict(self.rtn_data)
        assert st['keycode'] == 117
        assert st['name'] == 'test117'
        assert st['direction'] == True
        assert st['hit'] == False
        assert st['invert'] == True
