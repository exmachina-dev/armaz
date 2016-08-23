# -*- coding: utf-8 -*-

import pytest

from ertza.exceptions import AbstractErtzaException, AbstractErtzaFatalException
from ertza.machine import AbstractMachineError, MachineError, SlaveMachineError
from ertza.machine import AbstractMachineTimeoutError, AbstractMachineFatalError
from ertza.machine import MachineTimeoutError, MachineFatalError
from ertza.machine import SlaveMachineTimeoutError, SlaveMachineFatalError


class Test_MachineExceptions(object):
    def setup_class(self):
        self.ae = AbstractMachineError()
        self.me = MachineError()
        self.se = SlaveMachineError()

        self.ate = AbstractMachineTimeoutError()
        self.afe = AbstractMachineFatalError()
        self.mte = MachineTimeoutError()
        self.mfe = MachineFatalError()
        self.ste = SlaveMachineTimeoutError()
        self.sfe = SlaveMachineFatalError()

    def test_inheritance(self):
        # Abstract machine errors inherits from AbstractErtzaException
        assert isinstance(self.ae, AbstractErtzaException) == True
        assert isinstance(self.afe, AbstractMachineError) == True
        assert isinstance(self.ate, AbstractMachineError) == True

        # Fatal errors inherits from AbstractErtzaFatalException
        assert isinstance(self.afe, AbstractErtzaFatalException) == True
        assert isinstance(self.mfe, AbstractErtzaFatalException) == True
        assert isinstance(self.sfe, AbstractErtzaFatalException) == True

        # Machine errors inherits from AbstractMachineError
        assert isinstance(self.me, AbstractMachineError) == True
        assert isinstance(self.se, AbstractMachineError) == True

        # Timeout machine errors inherits from AbstractTimeouError
        assert isinstance(self.mte, AbstractMachineTimeoutError) == True
        assert isinstance(self.ste, AbstractMachineTimeoutError) == True

        # Fatal errors inherits from AbstractMachineFatalError
        assert isinstance(self.mfe, AbstractMachineFatalError) == True
        assert isinstance(self.sfe, AbstractMachineFatalError) == True

        # Machine errors inherits from MachineError
        assert isinstance(self.mfe, MachineError) == True
        assert isinstance(self.mte, MachineError) == True

        # Slave machine errors inherits from SlaveMachineError
        assert isinstance(self.sfe, SlaveMachineError) == True
        assert isinstance(self.ste, SlaveMachineError) == True

    def test_timeout_event(self):
        # Timeout event must be set at instanciation
        assert self.ate.timeout_event.is_set() == True
        assert self.mte.timeout_event.is_set() == True
        assert self.ste.timeout_event.is_set() == True

        # Timeouts between MachineTimeoutError and SlaveMachineError must be
        # separated
        self.ste.timeout_event.clear()
        self.ate.timeout_event.set()

        assert self.ate.timeout_event.is_set() == True
        assert self.mte.timeout_event.is_set() == True
        assert self.ste.timeout_event.is_set() == False

        self.mte.timeout_event.clear()
        self.ste.timeout_event.set()

        assert self.ate.timeout_event.is_set() == False
        assert self.mte.timeout_event.is_set() == False
        assert self.ste.timeout_event.is_set() == True

    def test_fatal_event(self):
        # Fatal event must be set at instanciation
        assert self.afe.fatal_event.is_set() == True
        assert self.mfe.fatal_event.is_set() == True
        assert self.sfe.fatal_event.is_set() == True

        # Fatals between MachineFatalError and SlaveMachineError must be
        # shared
        self.sfe.fatal_event.clear()
        self.afe.fatal_event.set()

        assert self.afe.fatal_event.is_set() == True
        assert self.mfe.fatal_event.is_set() == True
        assert self.sfe.fatal_event.is_set() == True

        self.sfe.fatal_event.set()
        self.mfe.fatal_event.clear()

        assert self.afe.fatal_event.is_set() == False
        assert self.mfe.fatal_event.is_set() == False
        assert self.sfe.fatal_event.is_set() == False
