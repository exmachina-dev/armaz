# -*- coding: utf-8 -*-

from ertza.base import BaseWorker
import ertza.errors as err

import time
import os

import configparser

user_config_path = os.path.expanduser('~/.ertza')
_DEFAULTS = {
        'log': {
            'log_path': os.path.join(user_config_path, 'logs'),
            },
        'osc': {
            'server_port': 7900,
            'client_port': 7901,
            },
        }

_CONFPATH = [
        '/etc/ertza/default.conf',
        os.path.join(user_config_path, 'ertza.conf'),
        ]


class ConfigWorker(BaseWorker):
    """
    Master process that handle configuration.
    """

    def __init__(self, sm):
        super(ConfigWorker, self).__init__(sm)
        self.get_logger()

        try:
            self.lg.debug('Reading configs: %s', self.cfpr.configs)
            self.cfpr.read_configs()
        except configparser.Error as e:
            error = err.ConfigError(e.message)
            self.lg.warn(error)
            raise error

        self.run()

    def run(self):
        self.config_event.set()
        while not self.exit_event.is_set():
            time.sleep(0.5)


class ConfigProxy(configparser.ConfigParser):
    """
    ConfigProxy provides an interface to a single ConfigParser instance.

    Helps sharing a simple config manager accross different processes.
    """

    def __init__(self):
        self._conf_path = _CONFPATH
        self.save_path = self._conf_path[-1]
        super(ConfigProxy, self).__init__(
                interpolation=configparser.ExtendedInterpolation()
        )
        self.read_dict(_DEFAULTS)

    def get(self, section, line, fallback=None):
        return super(ConfigProxy, self).get(section, line, fallback=fallback)


    def read_configs(self, path=None):
        if path and os.path.exists(path):
            self._conf_path.append(path)

        return self.read(self._conf_path)

    @property
    def configs(self):
        return self._conf_path

    def save(self):
        with open(self.save_path, 'w') as configfile:
            super(ConfigProxy, self).write(configfile)
