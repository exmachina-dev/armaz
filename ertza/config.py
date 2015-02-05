# -*- coding: utf-8 -*-

from ertza.base import BaseWorker
import ertza.errors as err

import time
import os

import configparser

import logging

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

_CONFPATH = ['/etc/ertza/default.conf',
        os.path.join(user_config_path, 'ertza.conf'),]


class ConfigWorker(BaseWorker):
    """
    Master process that handle configuration.
    """

    def __init__(self, sm):
        super(ConfigWorker, self).__init__(sm)
        self.get_logger()

        try:
            self.lg.debug('Reading configs…')
            self.cfpr.read_configs()
            self.lg.debug('Done.')
        except configparser.Error as e:
            self.lg.warn('Unable to load config: %s', e)
            raise err.ConfigError(e)

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
        super(ConfigProxy, self).__init__(
                defaults=_DEFAULTS,
                interpolation=configparser.ExtendedInterpolation()
        )
        self._conf_path = _CONFPATH

    def read_configs(self, path=None):
        if path and os.path.exists(path):
            self._conf_path.append(path)

        return self.read(self._conf_path)
