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

        self.watched_options = {
                'osc': {
                    'server_port': None
                    },
                }

        try:
            self.lg.debug('Reading configs: %s', self.cfpr.configs)
            missing = self.cfpr.read_configs()
            self.lg.debug('Missing configs: %s', missing)
            self.lg.debug(self.cfpr.dump())
            self._watchconfig(init=True)
        except configparser.Error as e:
            error = err.ConfigError(e.message)
            self.lg.warn(error)
            raise error

        self.run()

    def run(self):
        self.config_event.set()
        while not self.exit_event.is_set():
            self._watchconfig()

            time.sleep(0.5)

    def _watchconfig(self, init=None):
        for s, o in self.watched_options.items():
            for o, v in o.items():
                try:
                    if self.cfpr[s][o] is not v:
                        if not init:
                            if s is 'osc' and o is 'server_port':
                                self.lg.debug("""
Server port as changed. Old port: %s. New port: %s
Triggering OSC event.
                                """, v, self.cfpr[s][o])
                                self.osc_event.set()
                        self.watched_options[s][o] = self.cfpr[s][o]
                except configparser.Error as e:
                    self.lg.debug(repr(e))


class ConfigProxy(configparser.ConfigParser):
    """
    ConfigProxy provides an interface to a single ConfigParser instance.

    Helps sharing a simple config manager accross different processes.
    """

    def __init__(self):
        self._conf_path = _CONFPATH
        self.save_path = self._conf_path[-1]
        self.autosave = True

        super(ConfigProxy, self).__init__(
                interpolation=configparser.ExtendedInterpolation()
        )

    def get(self, section, line=None, fallback=None):
        return super(ConfigProxy, self).get(section, line, fallback=fallback)

    def set(self, section, option, value=None):
        rtn = super(ConfigProxy, self).set(section, option, value)
        if self.autosave:
            self.save()

        return rtn

    def read_configs(self, path=None):
        # Don't auto save when reading config
        asave = self.autosave
        self.autosave

        if path and os.path.exists(path):
            path = os.path.expanduser(path)
            if path in self._conf_path:
                raise ValueError('%s is already present.' % path)
            self._conf_path.append(path)

        try:
            rtn = self.read(self._conf_path)
            missing = set(self._conf_path) - set(rtn)
            if missing == set(self._conf_path):
                raise configparser.ParsingError('No config file found.')
        except configparser.ParsingError as e:
            self.read_hard_defaults()
            self.save()

        # Restore previous self.autosave state
        self.autosave = asave
        return list(missing)

    def read_hard_defaults(self):
        return self.read_dict(_DEFAULTS)

    @property
    def configs(self):
        return self._conf_path

    def save(self):
        with open(self.save_path, 'w') as configfile:
            super(ConfigProxy, self).write(configfile)

    def dump(self):
        for s, o in self.items():
            print('|— %s' % s)
            for o, v in o.items():
                print('|  |— %s: %s' % (o, v))


if __name__ == "__main__":
    cf = ConfigProxy()
    cf.read_configs()
    print(cf.configs)
    print('Config:')
    print(cf.dump())
