# -*- coding: utf-8 -*-

from ..base import BaseWorker
from .osc import OSCServer
from .osc.slave import SlaveServer, SlaveRequest, SlaveResponse
from .modbus import ModbusMaster, ModbusRequest, ModbusResponse
from ..errors import OSCServerError, ModbusMasterError, SlaveError

import time

class RemoteWorker(BaseWorker):
    """
    Master process that handle all communication instances:
        - Discret I/Os
        - Accessories serial bus
        - LCD display
    """

    def __init__(self, sm):
        super(RemoteWorker, self).__init__(sm)
        self.interval = 0.01

        self.cnf_pipe = self.initializer.cnf_rmt_pipe[1]
        self.mdb_pipe = self.initializer.mdb_rmt_pipe[1]
        self.slv_pipe = self.initializer.slv_rmt_pipe[1]

        self.get_logger()
        self.lg.debug("Init of RemoteWorker")

        self.wait_for_config()

        self.run()

    def run(self):
        while not self.exit_event.is_set():
            time.sleep(self.interval)
            if self.restart_rmt_event.is_set():
                self.lg.info('Remote server restarting…')
                self.init_rmt_server(True)
                self.restart_rmt_event.clear()


class OSCWorker(BaseWorker):
    """
    Master process that handle OSCServer:
    """

    def __init__(self, sm):
        super(OSCWorker, self).__init__(sm)
        self.interval = 0.005

        self.cnf_pipe = self.initializer.cnf_osc_pipe[1]
        self.mdb_pipe = self.initializer.mdb_osc_pipe[1]
        self.slv_pipe = self.initializer.slv_osc_pipe[1]

        self.get_logger()
        self.lg.debug("Init of OSCWorker")

        self.wait_for_config()
        self.run()

    def run(self):
        try:
            self.init_osc_server()
        except OSCServerError as e:
            self.lg.warn(e)
            self.exit()

        while not self.exit_event.is_set():
            self.osc_server.run(self.interval)
            if self.restart_osc_event.is_set():
                self.lg.info('OSC server restarting…')
                self.init_osc_server(True)
                self.restart_osc_event.clear()

            time.sleep(self.interval)

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
        self.interval = 0.005

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

            time.sleep(self.interval)

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
        self.interval = 0.005

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

            time.sleep(self.interval)

    def init_osc_slave(self, restart=False):
        if restart:
            del self.slave_server
        self.slave_server = SlaveServer(self.cnf_pipe, self.lg,
                self.restart_slv_event, self.blockall_event, self.mdb_pipe)
        self.slave_server.start(blocking=False)
        self.slave_server.announce()


__all__ = ['RemoteWorker', 'OSCWorker', 'ModbusWorker', 'SlaveWorker']
