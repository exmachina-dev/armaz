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


class ConfigProxy(object):
    """
    ConfigProxy provides an interface to a single ConfigParser instance.

    Helps sharing a simple config manager accross different processes.
    """

    _obj = configparser.ConfigParser(
            defaults=_DEFAULTS,
            interpolation=configparser.ExtendedInterpolation()
    )
    _conf_path = _CONFPATH

    def __getattribute__(self, name):
        return getattr(object.__getattribute__(self, "_obj"), name)

    def __delattr__(self, name):
        delattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_obj"), name, value)
        logging.debug("%s set to %s", name, value)


    def __nonzero__(self):
        return bool(object.__getattribute__(self, "_obj"))

    def __str__(self):
        return str(object.__getattribute__(self, "_obj"))

    def __repr__(self):
        return repr(object.__getattribute__(self, "_obj"))

    @classmethod
    def read_configs(cls, path=None):
        if os.path.exists(path):
            cls._conf_path.append(path)

        return cls._obj.read(cls._conf_path)



    #def __getitem__(self, key):
    #    return object.__getitem__(self, key)

    #def __delitem__(self, key):
    #    object.__delitem__(self, key)

    #def __setitem__(self, key, value):
    #    object.__setitem__(self, key, value)
