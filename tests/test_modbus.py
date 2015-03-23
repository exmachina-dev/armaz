# -*- coding: utf-8 -*-

import pytest
import configparser

from ertza.remotes.modbus import ModbusRequest
from ertza.remotes.modbus import ModbusBackend
from ertza.utils.fake import FakeModbus

class Test_ModbusRequest(object):
    def setup_class(self):
        self.rq = ModbusRequest(FakeModbus())

    def test_get(self):
        assert self.rq.status == \
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

class Test_ModbusBitOperations(object):
    def test_int(self):
        start_int = 1564862
        b = ModbusBackend._from_int(start_int)
        end_int = ModbusBackend._to_int(b[0]+b[1])
        assert start_int == end_int

    def test_float(self):
        start_float = 541.5486
        b = ModbusBackend._from_float(start_float)
        end_float = ModbusBackend._to_float(b[0]+b[1])
        assert start_float == round(end_float, 4)
