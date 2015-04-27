# -*- coding: utf-8 -*-

import os

_user_config_path = os.path.expanduser('~/.ertza')

OSC_REFRESH_RATE = 1000 # Hz
MDB_REFRESH_RATE = 1000 # Hz
SLV_REFRESH_RATE = 1500 # Hz
RMT_REFRESH_RATE = 500 # Hz

CNF_REFRESH_RATE = 100 # Hz
LOG_REFRESH_RATE = 100 # Hz

CONTROL_MODES = ('osc', 'swill', 'slave')
DEFAULT_CONTROL_MODE = CONTROL_MODES[0]

DEFAULT_CONFIG= {
        'log': {
            'log_path': _user_config_path,
            },
        'osc': {
            'server_port': 7900,
            'client_port': 7901,
            'broadcast': '192.168.1.255',
            },
        'modbus': {
            'device': '192.168.100.2',
            'node_id' : 2,
            'port': 502,
            },
        'enslave': {
            'mode': 'master',
            'server_port': 7900,
            'client_port': 7901,
            'broadcast': '192.168.1.255',
            'slaves_datastore': os.path.join(_user_config_path, 'slaves.dat')
            },
        'control': {
            'mode': DEFAULT_CONTROL_MODE,
            },
        'switch0': {
            'action': None,
            'reverse': False,
            },
        'switch1': {
            'mode': None,
            'reverse': False,
            },
        }

CONFIG_PATHS = (
        '/etc/ertza/default.conf',
        os.path.join(_user_config_path, 'ertza.conf'),
        )
