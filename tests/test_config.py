# -*- coding: utf-8 -*-

import pytest
import configparser

from ertza.config import ConfigRequest, _DEFAULTS
from ertza.utils.fake import FakeConfig

class Test_ConfigRequest(object):
    def setup_class(self):
        self.rq = ConfigRequest(FakeConfig())

    def test_get(self):
        assert int(self.rq.get('osc', 'server_port', 0)) == \
                _DEFAULTS['osc']['server_port']

        with pytest.raises(configparser.NoSectionError):
            self.rq.get('fake_section', 'fake_option')

        assert self.rq.get('fake_section', 'fake_option', 1234) == 1234

    def test_set(self):
        with pytest.raises(configparser.NoSectionError):
            self.rq.set('str', 'str', 0)

        with pytest.raises(ValueError):
            self.rq.set('osc', 0)

        with pytest.raises(ValueError):
            self.rq.set('str', 'str')

        rp = self.rq.set('osc', 'client_port', 4567)
        assert rp == '4567'
