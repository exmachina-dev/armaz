# -*- coding: utf-8 -*-

import os
import configparser

from .defaults import DEFAULT_CONFIG, CONFIG_PATHS


class BaseConfigParser(configparser.ConfigParser):
    """
    BaseConfigParser provides some helpers function for
    configparser.ConfigParser.

    Helps sharing a simple config manager accross different processes.
    """

    def __init__(self):
        self._conf_path = CONFIG_PATHS
        self.save_path = self._conf_path[-1]
        self.autosave = True

        super(BaseConfigParser, self).__init__(
                interpolation=configparser.ExtendedInterpolation()
        )

    def set(self, section, option, value=None):
        super(BaseConfigParser, self).set(section, option, value)
        if self.autosave:
            self.save()

        return super(BaseConfigParser, self).get(section, option)

    def read_configs(self, path=None):
        # Don't auto save when reading config
        asave = self.autosave
        self.autosave = False

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
        return self.read_dict(DEFAULT_CONFIG)

    @property
    def configs(self):
        return self._conf_path

    def save(self):
        with open(self.save_path, 'w') as configfile:
            super(BaseConfigParser, self).write(configfile)

    def dump(self, section=None):
        output = {}
        for s, o in self.items():
            for o, v in o.items():
                output.update({(s, o): v,})

        return output
