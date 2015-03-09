# -*- coding: utf-8 -*-

import time
import logging
import logging.handlers


class BaseWorker(object):
    """
    Base worker for multiprocessing.Manager()
    """

    interval = 0.5

    def __init__(self, sm):
        self.initializer = sm
        self.sm = sm.manager
        self.lgq = sm.log_queue

        self.cmd_args = sm.cmd_args

        # Some events
        self.exit_event = sm.exit_event
        self.blockall_event = sm.blockall_event
        self.cnf_ready_event = sm.cnf_ready_event
        self.slv_ready_event = sm.slv_ready_event

        self.restart_osc_event = sm.restart_osc_event
        self.restart_mdb_event = sm.restart_mdb_event
        self.restart_slv_event = sm.restart_slv_event

        self.config_lock = sm.config_lock
        self.init_lock = sm.init_lock

        self.running = True

    def get_logger(self, name=__name__):
        _h = logging.handlers.QueueHandler(self.lgq) # Just the one handler needed
        self.lg = logging.getLogger(name)
        self.lg.addHandler(_h)
        self.lg.setLevel(logging.DEBUG)

    def run(self):
        pass

    def wait_for_config(self):
        while not self.cnf_ready_event.is_set():
            time.sleep(self.interval)

    def wait_for_slaves(self):
        while not self.slv_ready_event.is_set():
            time.sleep(self.interval)

    def exit(self, reason=None):
        if reason:
            self.lg.warn('Exit with: %s', reason)
        self.exit_event.set()


class BaseCommunicationObject(object):
    _command = {
            'get':                      0b00000001,
            'set':                      0b00000010,
            'dmp':                      0b00000100,
            'reg':                      0b00001000,
            }
    _methods = {
            'get_status':               (0b00000001 << 8) + _command['get'],
            'get_command':              (0b00000010 << 8) + _command['get'],
            'set_command':              (0b00000010 << 8) + _command['set'],
            'get_error_code':           (0b00000011 << 8) + _command['get'],
            'get_drive_temperature':    (0b00000100 << 8) + _command['get'],
            'register_slave':           (0b00000101 << 8) + _command['reg'],
            'unregister_slave':         (0b00000110 << 8) + _command['reg'],
            'set_master':               (0b00000111 << 8) + _command['set'],
            'get_master':               (0b00000111 << 8) + _command['get'],
            'set_mode':                 (0b00001000 << 8) + _command['set'],
            'get_mode':                 (0b00001000 << 8) + _command['get'],
            }

    _methods.update(_command)

    def __init__(self, target, *args):
        self.target = target
        self.method = None
        self.value = None
        self.args = None

        if args:
            self.args = args

    def send(self):
        if self.method:
            return self.target.send(self)
        else:
            raise ValueError("Method isn't defined.")

    def __str__(self):
        return '%s %s %s' % (self.method, self.args, self.value)

    __repr__ = __str__


class BaseRequest(BaseCommunicationObject):
    def send(self):
        super(BaseRequest, self).send()
        rp = self.target.recv()
        return rp

    def _check_args(self, *args):
        self.args = args
        if self.args:
            self.method = None
            self.value = None

    def _build_rq(self, method, *args):
        self._check_args(*args)
        self.method = self._methods[method]
        rp = self.send()
        return rp.value


class BaseResponse(BaseCommunicationObject):
    pass
