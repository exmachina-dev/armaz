# -*- coding: utf-8 -*-

import os

_user_config_path = os.path.expanduser('~/.ertza')

_DEFAULTS = {
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
        }

_CONFPATH = [
        '/etc/ertza/default.conf',
        os.path.join(_user_config_path, 'ertza.conf'),
        ]

_CONTROL_MODES = ('osc', 'serial', 'slave')
