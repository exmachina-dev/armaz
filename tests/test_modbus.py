# -*- coding: utf-8 -*-

import pytest
import configparser

from ertza.drivers.modbus import ModbusDriver
from ertza.drivers.modbus import ModbusDriverFrontend
from ertza.drivers.modbus import ModbusBackend

class Test_ModbusDriver(object):
    def setup_class(self):
        self.dr = ModbusDriver({'target_address': '127.0.0.1', 'target_port': '502'})
        self.attrs = self.dr.get_attribute_map()

    def test_get(self):
        with pytest.raises(KeyError):
            self.dr['nonexistingkey']

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

    def test_bools(self):
        start_bools = (True, False, True, False, False, True, False, True,) * 2
        b = ModbusBackend._from_bools(start_bools)
        end_bools = ModbusBackend._to_bools(b[0]+b[1])
        assert list(start_bools) == end_bools
