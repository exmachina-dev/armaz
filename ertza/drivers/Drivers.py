# -*- coding: utf-8 -*-


class Driver(object):
    _drivers = None

    def __new__(cls):
        Driver._drivers = Driver._get_drivers()
        return super(Driver, cls).__new__(cls)

    def get_driver(self, driver):
        return Driver._drivers[driver]

    @classmethod
    def _get_drivers(cls):
        drv = {}
        from drivers.Modbus import ModbusDriver
        from drivers.Osc import OscDriver

        drv['Modbus'] = ModbusDriver
        drv['Osc'] = OscDriver

        return drv
