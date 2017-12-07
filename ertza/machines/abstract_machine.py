# -*- coding: utf-8 -*-

from enum import Enum, unique
from threading import Event

from .types import MachineType
from .control_mode import ControlMode


class AbstractMachineError(Exception):
    pass


class AbstractFatalMachineError(AbstractMachineError):
    pass


@unique
class MotionModes(Enum):
    VELOCITY = 1
    POSITION = 2
    TORQUE = 3
    ENHANCED_TORQUE = 4


class AbstractMachine(object):

    def __init__(self):
        self.machine_type = MachineType.NONE
        self._serialnumber = None
        self._version = None
        self._control_mode = None

        self.config = None          # Machine specific config
        self.driver = None          # Driver for communication with the machine

        self.fatal_error_ev = Event()   # A fatal error that will stop the movement
        self.warning_ev = Event()       # A warning issued by the attached machine
        self.timeout_ev = Event()       # A timeout occured

    def init_driver(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def exit(self):
        raise NotImplementedError

    def reply(self, command):
        raise NotImplementedError

    def send_message(self, msg):
        raise NotImplementedError

    @property
    def infos(self):
        raise NotImplementedError

    @property
    def serialnumber(self):
        raise NotImplementedError

    @property
    def address(self):
        raise NotImplementedError
