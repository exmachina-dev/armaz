# -*- coding: utf-8 -*-

from ..base import BaseWorker
from ..errors import ConfigError
from .parser import BaseConfigParser as ConfigParser
from .communication import ConfigRequest, ConfigResponse
from .defaults import CONTROL_MODES, DEFAULT_CONTROL_MODE, CNF_REFRESH_RATE

import sys
import time

from configparser import Error


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

        self.interval = 1 / CNF_REFRESH_RATE

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
        except Error as e:
            raise ConfigError(e.message, self.lg)

        self.run()

    def run(self):
        self.cnf_ready_event.set()
        try:
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
        except ConnectionError:
            sys.exit()

    def _watchconfig(self, response):
        if not response.method == ConfigResponse._methods['set']:
            return None
        if response.request.args[0] in self.watched_options:
            section = response.request.args[0]
            if response.request.args[1] in self.watched_options[section]:
                option = response.request.args[1]
                self.lg.debug(
                        'Watched item changed: %s.%s\n\tNew value: %s' % (
                            section, option, response.value))
                self.watched_options[section][option]()



if __name__ == '__main__':
    cf = ConfigParser()
    cf.read_configs()
    print(cf.configs)
    print('Config:')
    print(cf.dump())
