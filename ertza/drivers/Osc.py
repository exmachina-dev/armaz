# -*- coding: utf-8 -*-

from drivers.AbstractDriver import AbstractDriver


class OscDriver(AbstractDriver):

    def __init__(self, config):
        self.target_address = config.get("target_address")
        self.target_port = config.get("target_port")
