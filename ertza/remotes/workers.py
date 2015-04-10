# -*- coding: utf-8 -*-

from ..base import BaseWorker
from .osc import OSCServer
from .osc.slave import SlaveServer, SlaveRequest, SlaveResponse
from .modbus import ModbusMaster, ModbusRequest, ModbusResponse
from .gpio import RemoteServer
from ..errors import RemoteServerError, RemoteError
from ..errors import OSCServerError
from ..errors import ModbusMasterError, SlaveError
from ..config.defaults import (RMT_REFRESH_RATE, OSC_REFRESH_RATE,
        MDB_REFRESH_RATE, SLV_REFRESH_RATE)

import time
import sys

class RemoteWorker(BaseWorker):
    """
    Master process that handle all communication instances:
        - Switchs
        - Accessories serial bus
        - LCD display
    """

    def __init__(self, sm):
        super(RemoteWorker, self).__init__(sm)
        self.interval = 1 / RMT_REFRESH_RATE

        self.cnf_pipe = self.initializer.cnf_rmt_pipe[1]
        self.mdb_pipe = self.initializer.mdb_rmt_pipe[1]
        self.slv_pipe = self.initializer.slv_rmt_pipe[1]

        self.get_logger()
        self.lg.debug("Init of RemoteWorker")

        self.wait_for_config()

        try:
            self.run()
        except KeyboardInterrupt:
            self.lg.info("Keyboard interrupt received: exiting.")
            exit(0)

    def run(self):
        try:
            self.init_rmt_server()
        except RemoteServerError as e:
            self.lg.warn(e)
            self.exit()

        try:
            while not self.exit_event.is_set():
                try:
                    self.rmt_server.run(self.interval)
                except RemoteError:
                    pass
                self.exit_event.wait(self.interval)
        except ConnectionError:
            sys.exit()

    def init_rmt_server(self, restart=False):
        if restart:
            self.rmt_server.restart()
            return True
        try:
            self.rmt_server = RemoteServer(self.cnf_pipe, logger=self.lg,
                    restart_event=self.restart_rmt_event, modbus=self.mdb_pipe,
                    slave=self.slv_pipe)
        except RemoteError:
            pass

class OSCWorker(BaseWorker):
    """
    Master process that handle OSCServer:
    """

    def __init__(self, sm):
        super(OSCWorker, self).__init__(sm)
        self.interval = 1 / OSC_REFRESH_RATE

        self.cnf_pipe = self.initializer.cnf_osc_pipe[1]
        self.mdb_pipe = self.initializer.mdb_osc_pipe[1]
        self.slv_pipe = self.initializer.slv_osc_pipe[1]

        self.get_logger()
        self.lg.debug("Init of OSCWorker")

        self.wait_for_config()
        try:
            self.run()
        except KeyboardInterrupt:
            self.lg.info("Keyboard interrupt received: exiting.")
            exit(0)

    def run(self):
        try:
            self.init_osc_server()
        except OSCServerError as e:
            self.lg.warn(e)
            self.exit()

        try:
            while not self.exit_event.is_set():
                self.osc_server.run(self.interval)
                if self.restart_osc_event.is_set():
                    self.lg.info('OSC server restarting…')
                    self.init_osc_server(True)
                    self.restart_osc_event.clear()

                self.exit_event.wait(self.interval)
        except ConnectionError:
            sys.exit()

    def init_osc_server(self, restart=False):
        if restart:
            del self.osc_server
        self.osc_server = OSCServer(self.cnf_pipe, logger=self.lg,
                restart_event=self.restart_osc_event, modbus=self.mdb_pipe,
                slave=self.slv_pipe)
        self.osc_server.start(blocking=False)
        self.osc_server.announce()


class ModbusWorker(BaseWorker):
    """
    Master process that handle ModbusBackend:
    """

    def __init__(self, sm):
        super(ModbusWorker, self).__init__(sm)
        self.interval = 1 / MDB_REFRESH_RATE

        try:
            self.fake_modbus = self.cmd_args.without_modbus
        except AttributeError:
            self.fake_modbus = False

        self.cnf_pipe = self.initializer.cnf_mdb_pipe[1]
        self.osc_pipe = self.initializer.mdb_osc_pipe[0]
        self.rmt_pipe = self.initializer.mdb_rmt_pipe[0]
        self.pipes = (self.osc_pipe, self.rmt_pipe)

        self.get_logger()
        self.lg.debug("Init of ModbusWorker")

        self.wait_for_config()
        self.run()

    def run(self):
        try:
            self.init_modbus()
        except ModbusMasterError as e:
            self.lg.warn(e)

        try:
            while not self.exit_event.is_set():
                if self.restart_mdb_event.is_set():
                    self.lg.info('Modbus master restarting…')
                    self.init_modbus(True)
                    self.restart_mdb_event.clear()
                else:
                    for pipe in self.pipes:
                        if pipe.poll():
                            rq = pipe.recv()
                            if not type(rq) is ModbusRequest:
                                raise ValueError('Unexcepted type: %s' % type(rq))
                            rs = ModbusResponse(pipe, rq, self.modbus_master.back)
                            rs.handle()
                            rs.send()

                self.exit_event.wait(self.interval)
        except ConnectionError:
            sys.exit()

    def init_modbus(self, restart=False):
        if restart:
            del self.modbus_backend
        self.modbus_master = ModbusMaster(self.cnf_pipe, self.lg,
                self.restart_mdb_event, self.blockall_event, self.fake_modbus)
        self.modbus_master.start()


class SlaveWorker(BaseWorker):
    """
    Process that handle slaves if started as master, or forward commands if
    started as slave.
    """

    def __init__(self, sm):
        super(SlaveWorker, self).__init__(sm)
        self.interval = 1 / SLV_REFRESH_RATE

        self.cnf_pipe = self.initializer.cnf_slv_pipe[1]
        self.osc_pipe = self.initializer.slv_osc_pipe[0]
        self.mdb_pipe = self.initializer.mdb_slv_pipe[1]
        self.rmt_pipe = self.initializer.mdb_rmt_pipe[1]
        self.pipes = (self.osc_pipe, self.mdb_pipe, self.rmt_pipe)

        self.get_logger()
        self.lg.debug("Init of SlaveWorker")

        self.wait_for_config()
        self.run()

    def run(self):
        try:
            self.init_osc_slave()
        except SlaveError as e:
            self.lg.warn(e)

        try:
            while not self.exit_event.is_set():
                self.slave_server.run(self.interval)
                if self.restart_slv_event.is_set():
                    self.lg.info('Slave worker restarting…')
                    self.init_osc_slave(True)
                    self.restart_slv_event.clear()
                else:
                    for pipe in self.pipes:
                        if pipe.poll():
                            rq = pipe.recv()
                            if not type(rq) is SlaveRequest:
                                raise ValueError('Unexcepted type: %s' % type(rq))
                            rs = SlaveResponse(pipe, rq, self.slave_server)
                            rs.handle()
                            rs.send()

                self.exit_event.wait(self.interval)
        except ConnectionError:
            sys.exit()

    def init_osc_slave(self, restart=False):
        if restart:
            del self.slave_server
        self.slave_server = SlaveServer(self.cnf_pipe, self.lg,
                self.restart_slv_event, self.blockall_event, self.mdb_pipe)
        self.slave_server.start(blocking=False)
        self.slave_server.announce()


__all__ = ['RemoteWorker', 'OSCWorker', 'ModbusWorker', 'SlaveWorker']
