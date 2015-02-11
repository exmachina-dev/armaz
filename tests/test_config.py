# -*- coding: utf-8 -*-

from ertza import config

class ConfigRequestTest(object):
    def setup_class(self):
        self.rq = config.ConfigRequest(None)

    def get_test(self):
        self.rq.get('str', 'str', 0)

        assert True
