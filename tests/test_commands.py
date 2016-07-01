# -*- coding: utf-8 -*-

import pytest

from ertza.commands import AbstractCommand, OscCommand, SerialCommand
from ertza.machine import AbstractMachine
from ertza.processors.osc.message import OscAddress, OscMessage
from ertza.processors.serial.message import SerialCommandString


class _FakeMachine(AbstractMachine):
    def send_message(self, m):
        return m


class Test_AbstractCommand(object):
    def setup_class(self):
        m = _FakeMachine()
        self.cmd = AbstractCommand(m)

    def test_alias(self):
        with pytest.raises(NotImplementedError):
            self.cmd.alias

    def test_execute(self):
        with pytest.raises(NotImplementedError):
            self.cmd.execute(None)

    def test_send(self):
        with pytest.raises(NotImplementedError):
            self.cmd.send(None)


class Test_OscCommand(object):
    def setup_class(self):
        self.fm = _FakeMachine()
        self.cmd = OscCommand(self.fm)

        class TestCommand(OscCommand):
            @property
            def alias(self):
                return '/test'

        self.tc = TestCommand

    def test_alias(self):
        with pytest.raises(NotImplementedError):
            self.cmd.alias

        c = self.tc(self.fm)
        assert c.alias == '/test'

    def test_send(self):
        t = OscAddress(hostname='127.0.0.1')

        c = self.cmd.send(t, '/machine/test')
        assert c.path == '/machine/test'

        c = self.cmd.send(t, '/', 1, 2, 3)
        assert c.path == '/'
        assert c.args == (1, 2, 3)

        c = self.cmd.send(t, '/', 1)
        assert c.args == (1,)

        c = self.tc(self.fm).send(t, '/')
        assert c.args == ()


class Test_SerialCommand(object):
    def setup_class(self):
        self.fm = _FakeMachine()
        self.cmd = SerialCommand(self.fm)

        SerialCommandString.SerialNumber = 'YYWWPPPPNNNN'

        class TestCommand(SerialCommand):
            @property
            def alias(self):
                return 'machine.test'

        self.tc = TestCommand

    def test_alias(self):
        with pytest.raises(NotImplementedError):
            self.cmd.alias

        c = self.tc(self.fm)
        assert c.alias == 'machine.test'

    def test_send(self):
        c = self.cmd.send('test')
        assert c.tobytes == b'ExmEisla\x00\x1cYYWWPPPPNNNNtest\r\n'
        assert len(c) == 28

        c = self.cmd.send('test', 1, 2, 3)
        assert c.tobytes == b'ExmEisla\x00\x2bYYWWPPPPNNNNtest:\x00\x00\x00\x01:\x00\x00\x00\x02:\x00\x00\x00\x03\r\n'
        assert len(c) == 43

        c = self.cmd.send('test', 'string')
        assert c.tobytes == b'ExmEisla\x00\x23YYWWPPPPNNNNtest:string\r\n'
        assert len(c) == 35

        c = self.cmd.send('test', 0.1)
        assert c.tobytes == b'ExmEisla\x00\x21YYWWPPPPNNNNtest:=\xcc\xcc\xcd\r\n'
        assert len(c) == 33

        c = self.cmd.send('test', True)
        assert c.tobytes == b'ExmEisla\x00!YYWWPPPPNNNNtest:\x00\x00\x00\x01\r\n'
        assert len(c) == 33

        c = self.cmd.send('test', False)
        assert c.tobytes == b'ExmEisla\x00!YYWWPPPPNNNNtest:\x00\x00\x00\x00\r\n'
        assert len(c) == 33
