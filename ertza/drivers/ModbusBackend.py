# -*- coding: utf-8 -*-

import logging
import bitstring

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.register_read_message import (ReadHoldingRegistersRequest,
                                            ReadHoldingRegistersResponse,
                                            ReadWriteMultipleRegistersRequest,
                                            ReadWriteMultipleRegistersResponse)
from pymodbus.register_write_message import (WriteMultipleRegistersRequest,
                                             WriteMultipleRegistersResponse)
from pymodbus.pdu import ExceptionResponse
import pymodbus.exceptions as pmde


class ModbusBackendError(Exception):
    pass


class ModbusBackend(object):
    min_netdata = 0
    max_netdata = 999
    register_nb_by_netdata = 2

    def __init__(self, target_addr, target_port, target_nodeid):
        self.address = target_addr
        self.port = target_port
        self.nodeid = target_nodeid

        self.connected = False

        self._end = ModbusClient(host=self.address, port=self.port)

    def connect(self):
        self.connected = self._end.connect()
        return self.connected

    def close(self):
        self._end.close()

    def write_netdata(self, netdata, data, data_format=None):
        self._check_netdata(netdata)
        start = netdata * self.register_nb_by_netdata

        if data_format:
            data = bitstring.pack(data_format, *data).unpack('uintbe:16,uintbe:16')
        else:
            data = bitstring.pack('uintbe:16,uintbe:16', *data)

        return self.wmr(start, data)

    def read_netdata(self, netdata, fmt):
        self._check_netdata(netdata)
        start = netdata * self.register_nb_by_netdata

        try:
            response = self.rhr(start)
            res = bitstring.BitArray('0b%s' % ''.join(response)).unpack(fmt)
        except TypeError as e:
            logging.error('Unexpected error: {!s}'.format(e))
            return
        return res

    def _read_holding_registers(self, address):
        count = self.register_nb_by_netdata
        rq = ReadHoldingRegistersRequest(address, count,
                                         unit_id=self.nodeid)
        return self._rq(rq)

    def _write_multiple_registers(self, address, value):
        rq = WriteMultipleRegistersRequest(address, value)

        return self._rq(rq)

    def _read_write_multiple_registers(self, address, value):
        rq = ReadWriteMultipleRegistersRequest(address, value,
                                               unit_id=self.nodeid)
        return self._rq(rq)

    def _check_netdata(self, netdata_address):
        if not (self.min_netdata <= netdata_address <= self.max_netdata):
            raise ValueError("Invalid netdata address: %d" % netdata_address)

    # Shortcuts
    rhr = _read_holding_registers
    wmr = _write_multiple_registers
    rwmr = _read_write_multiple_registers

    def _rq(self, rq, **kwargs):
        """
        Executes a Modbus request and return the response.
        """

        try:
            if not self.connected:
                logging.info("Not connected, connecting...")
                if not self.connect():
                    raise ModbusBackendError('Unable to connect.')

            response = self._end.execute(rq)
            rpt = type(response)
            if rpt == ExceptionResponse:
                raise IOError('Exception received during execution.')
            elif rpt == WriteMultipleRegistersResponse:
                return True
            elif rpt == ReadHoldingRegistersResponse or \
                    rpt == ReadWriteMultipleRegistersResponse:
                regs = list()
                fmt = "{:0>16b}"
                for i in range(self.register_nb_by_netdata):
                    regs.append(fmt.format(response.getRegister(i)))
                return ''.join(regs)
        except pmde.ConnectionException:
            self.connected = False
            raise IOError('Unable to connect to slave')
