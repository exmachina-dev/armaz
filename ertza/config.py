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

            time.sleep(self.interval)

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


class BaseConfigParser(configparser.ConfigParser):
    """
    BaseConfigParser provides some helpers function for
    configparser.ConfigParser.

    Helps sharing a simple config manager accross different processes.
    """

    def __init__(self):
        self._conf_path = _CONFPATH
        self.save_path = self._conf_path[-1]
        self.autosave = True

        super(BaseConfigParser, self).__init__(
                interpolation=configparser.ExtendedInterpolation()
        )

    def set(self, section, option, value=None):
        rtn = super(BaseConfigParser, self).set(section, option, value)
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
            raise e

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
            super(BaseConfigParser, self).write(configfile)

    def dump(self):
        output = ''
        for s, o in self.items():
            output += ('[ %s : ( ' % s)
            for o, v in o.items():
                output += ('%s: %s — ' % (o, v))
            output += (']')

        return output


class ConfigProxy(BaseConfigParser):
    """
    ConfigProxy provides an interface to a single BaseConfigParser instance.

    Helps sharing a simple config manager accross different processes.
    """


    _obj = BaseConfigParser()

#    def __new__(cls):
#        if cls._obj is None:
#          i = BaseConfigParser.__new__(cls)
#          cls._obj = i
#        else:
#          i = cls._obj
#        return i

    def __init__(self, *args, **kw):
        return getattr(object.__getattribute__(self, "_obj"),
                "__init__")(*args, **kw)

    def __getattribute__(self, name):
        return getattr(object.__getattribute__(self, "_obj"), name)

    def __getitem__(self, *args, **kw):
        return getattr(object.__getattribute__(self, "_obj"),
                "__getitem__")(*args, **kw)

    def __setitem__(self, *args, **kw):
        return getattr(object.__getattribute__(self, "_obj"),
                "__setitem__")(*args, **kw)

    def __delitem__(self, *args, **kw):
        return getattr(object.__getattribute__(self, "_obj"),
                "__delitem__")(*args, **kw)

    def __contains__(self, *args, **kw):
        return getattr(object.__getattribute__(self, "_obj"),
                "__contains__")(*args, **kw)

    def __len__(self, *args, **kw):
        return getattr(object.__getattribute__(self, "_obj"),
                "__len__")(*args, **kw)

    def __iter__(self, *args, **kw):
        return getattr(object.__getattribute__(self, "_obj"),
                "__iter__")(*args, **kw)

ConfigParser = BaseConfigParser

if __name__ == '__main__':
    cf = ConfigParser()
    cf.read_configs()
    print(cf.configs)
    print('Config:')
    print(cf.dump())
