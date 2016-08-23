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
import functools
import time

from ertza.switch import Switch

logging.basicConfig()
logger = logging.getLogger('ertza')


class Test_Switch(object):
    def _write_to_inputdev(self, key, hit):
        ev = bytearray(b'\x00' * 32)
        ev[10] = key
        ev[12] = int(hit)

        with open(self.inputdev, 'wb') as f:
            f.write(bytes(ev))

    def setup_class(self):
        self.inputdev = os.path.realpath('./tests/inputdev')
        self.data_ev = Event()
        self.wait_ev = Event()
        self.rtn_data = {}

        with open(self.inputdev, 'w') as f:
            pass

        def _cb(sw_state):
            self.wait_ev.wait()
            self.data_ev.clear()

            self.rtn_data = sw_state.copy()
            self.data_ev.set()

        Switch.callback = _cb
        Switch.set_inputdev(self.inputdev)

    def test_non_existing_inpudev_file(self):
        with pytest.raises(FileNotFoundError):
            Switch.set_inputdev('./tests/nonexisting_dir')

        Switch.set_inputdev(self.inputdev)

    def test_switch(self):
        self.data_ev.clear()
        Switch(115, 'test115')
        Switch(116, 'test116')
        Switch(117, 'test117', invert=True)
        Switch.start()

        self._write_to_inputdev(115, True)
        self.wait_ev.set()
        self.data_ev.wait()
        st = dict(self.rtn_data)
        self.data_ev.clear()
        self.wait_ev.clear()
        assert st['keycode'] == 115
        assert st['name'] == 'test115'
        assert st['hit'] == True

        self._write_to_inputdev(116, True)
        self.wait_ev.set()
        self.data_ev.wait()
        st = dict(self.rtn_data)
        self.wait_ev.clear()
        assert st['keycode'] == 116
        assert st['name'] == 'test116'
        assert st['hit'] == True
        assert st['invert'] == False

        self._write_to_inputdev(117, True)
        self.wait_ev.set()
        self.data_ev.wait()
        st = dict(self.rtn_data)
        self.data_ev.clear()
        self.wait_ev.clear()
        assert st['keycode'] == 117
        assert st['name'] == 'test117'
        assert st['hit'] == True
        assert st['invert'] == True
