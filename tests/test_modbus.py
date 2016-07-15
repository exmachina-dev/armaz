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
