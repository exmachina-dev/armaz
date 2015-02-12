# -*- coding: utf-8 -*-

from ertza import config

class Test_ConfigRequest(object):
    def setup_class(self):
        self.rq = config.ConfigRequest(config.ConfigParser)

    def test_get(self):
        assert self.rq.get('str', 'str', 0) == 0
