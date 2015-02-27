# -*- coding: utf-8 -*-

import pytest
import configparser

from ertza.remotes.modbus import ModbusRequest
from ertza.utils.fake import FakeModbus

class Test_ModbusRequest(object):
    def setup_class(self):
        self.rq = ModbusRequest(FakeModbus())

    def test_get(self):
        assert self.rq.get_status() == \
                None

        with pytest.raises(configparser.NoSectionError):
            self.rq.get('fake_section', 'fake_option')

        assert self.rq.get('fake_section', 'fake_option', 1234) == 1234

    def test_set(self):
        with pytest.raises(configparser.NoSectionError):
            self.rq.set('str', 'str', 0)

        with pytest.raises(ValueError):
            self.rq.set('osc', 0)

        with pytest.raises(ValueError):
            self.rq.set('str', 'str')

        rp = self.rq.set('osc', 'client_port', 4567)
        assert rp == '4567'
