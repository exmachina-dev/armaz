# -*- coding: utf-8 -*-

from ..base import BaseResponse, BaseRequest
from ..errors import ConfigError
from .defaults import CONTROL_MODES, DEFAULT_CONTROL_MODE

from configparser import NoSectionError


class ConfigRequest(BaseRequest):
    def get(self, *args):
        return self._build_rq('get', *args)

    def set(self, *args):
        return self._build_rq('set', *args)

    def dump(self, *args):
        return self._build_rq('dmp', *args)

    def sections(self):
        return self._build_rq('sec')


class ConfigResponse(BaseResponse):
    def __init__(self, target=None, request=None, config=None, *args):
        super(ConfigResponse, self).__init__(target, *args)
        self.request = request
        self._config = config

    def get_from_config(self, *args):
        self.method = self._methods['get']

        if not self._config:
            raise ValueError("Config isn't defined.")

        try:
            if len(args) == 3:
                section, option, fallback = args
                self.value = self._config.get(section, option, fallback=fallback)
            elif len(args) == 2:
                section, option = args
                self.value = self._config.get(section, option)
        except NoSectionError as e:
            self.value = None
            raise ConfigError(e, self.lg)

    def set_to_config(self, *args):
        self.method = self._methods['set']

        if not self._config:
            raise ValueError("Config isn't defined.")
        if len(args) == 3:
            section, option, value = args
        else:
            raise ValueError("One or more argument is missing.")
        self.value = self._config.set(str(section), str(option), str(value))

    def dump_config(self, *args):
        self.method = self._methods['dmp']

        if not self._config:
            raise ValueError("Config isn't defined.")
        if len(args) == 1:
            section, = args
        else:
            section = None
        self.value = self._config.dump(str(section))

    def get_sections(self):
        self.method = self._methods['sec']

        self.value = self._config.sections()

    def handle(self):
        args = self.request.args
        if self.request.method == self._methods['set']:
            self.set_to_config(*args)
        elif self.request.method == self._methods['get']:
            self.get_from_config(*args)
        elif self.request.method == self._methods['dmp']:
            self.dump_config(*args)
        elif self.request.method == self._methods['sec']:
            self.get_sections(*args)
        else:
            raise ValueError('Unexcepted method: %s', self.request.method)

        return self.value
