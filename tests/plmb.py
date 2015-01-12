#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pylibmodbus import ModbusRtu

mb = ModbusRtu()
mb.connect()
mb.rtu_set_serial_mode(0)
nb = 5

print("W [0, 0, 0, 0, 0]")
data = [0] * nb
mb.write_register(0, data)

print("R")
data = mb.read_registers(0, nb)
for i, v in enumerate(data):
    print("%d: %d" % (i, v))

print("W [0, 1, 2, 3, 4]")
data = list(range(nb))
mb.write_register(0, data)

print("R")
data = mb.read_registers(0, nb)
for i, v in enumerate(data):
    print("%d: %d" % (i, v))
