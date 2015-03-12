# -*- coding: utf-8 -*-

from .base import BaseWorker, BaseResponse, BaseRequest
from .errors import ConfigError
from .defaults import DEFAULT_CONFIG, CONFIG_PATHS
from .defaults import CONTROL_MODES, DEFAULT_CONTROL_MODE

import time
import os

import configparser


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


ConfigParser = BaseConfigParser


class ConfigRequest(BaseRequest):
    def get(self, *args):
        return self._build_rq('get', *args)

    def set(self, *args):
        return self._build_rq('set', *args)

    def dump(self, *args):
        return self._build_rq('dmp', *args)


class ConfigResponse(BaseResponse):
    def __init__(self, target, request, config=None, *args):
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
        except configparser.NoSectionError as e:
            self.value = None
            raise(ConfigError(e))

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

    def handle(self):
        args = self.request.args
        if self.request.method == self._methods['set']:
            self.set_to_config(*args)
        elif self.request.method == self._methods['get']:
            self.get_from_config(*args)
        elif self.request.method == self._methods['dmp']:
            self.dump_config(*args)
        else:
            raise ValueError('Unexcepted method: %s', self.request.method)

        return self.value


class ConfigWorker(BaseWorker):
    """
    Master process that handle configuration.
    """

    _config = ConfigParser

    def __init__(self, sm):
        super(ConfigWorker, self).__init__(sm)
        self.log_pipe = self.initializer.cnf_log_pipe[0]
        self.rmt_pipe = self.initializer.cnf_rmt_pipe[0]
        self.osc_pipe = self.initializer.cnf_osc_pipe[0]
        self.mdb_pipe = self.initializer.cnf_mdb_pipe[0]
        self.slv_pipe = self.initializer.cnf_slv_pipe[0]
        self.pipes = (self.log_pipe, self.rmt_pipe, self.osc_pipe,
                self.mdb_pipe, self.slv_pipe)

        self.interval = 0.001

        self._config = self._config()

        self.get_logger()

        def _restart_slv_rmt_osc():
            self.restart_slv_event.set()
            self.restart_rmt_event.set()
            self.restart_osc_event.set()

        self.watched_options = {
                'osc': {
                    'server_port': self.restart_osc_event.set
                    },
                'modbus': {
                    'device': self.restart_mdb_event.set,
                    'node_id': self.restart_mdb_event.set,
                    },
                'enslave': {
                    'server_port': self.restart_slv_event.set,
                    'client_port': self.restart_slv_event.set,
                    'mode': self.restart_slv_event.set,
                    'master': self.restart_slv_event.set,
                    },
                'control': {
                    'mode': _restart_slv_rmt_osc,
                    'switch_0_mode': self.restart_rmt_event.set,
                    'switch_1_mode': self.restart_rmt_event.set,
                    'switch_0_inversed': self.restart_rmt_event.set,
                    'switch_1_inversed': self.restart_rmt_event.set,
                    },
                }

        try:
            self.lg.debug('Reading configs: %s', self._config.configs)
            missing = self._config.read_configs()
            self.lg.info('Missing configs: %s', missing)
        except configparser.Error as e:
            raise ConfigError(e.message, self.lg)

        self.run()

    def run(self):
        self.cnf_ready_event.set()
        while not self.exit_event.is_set():
            for pipe in self.pipes:
                if pipe.poll():
                    rq = pipe.recv()
                    if not type(rq) is ConfigRequest:
                        raise ValueError('Unexcepted type: %s' % type(rq))
                    rs = ConfigResponse(pipe, rq, self._config)
                    rs.handle()
                    self._watchconfig(rs)
                    rs.send()


            time.sleep(self.interval)

    def _watchconfig(self, response):
        if not response.method == ConfigResponse._methods['set']:
            return None
        if response.request.args[0] in self.watched_options:
            section = response.request.args[0]
            if response.request.args[1] in self.watched_options[section]:
                option = response.request.args[1]
                self.lg.debug('Watched item changed: %s.%s' % (section, option,))
                self.watched_options[section][option]()


__all__ = ['ConfigRequest', 'ConfigResponse', 'ConfigWorker', 'ConfigParser']

if __name__ == '__main__':
    cf = ConfigParser()
    cf.read_configs()
    print(cf.configs)
    print('Config:')
    print(cf.dump())
