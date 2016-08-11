# -*- coding: utf-8 -*-

import logging

from ..abstract_driver import AbstractDriver, AbstractDriverError
from ..frontend import DriverFrontend
from ..netdata_maps import MicroflexE100Map

from .backend import ModbusBackend, ModbusBackendError

from ..utils import retry

logging = logging.getLogger('ertza.drivers.modbus')

class ModbusDriverError(AbstractDriverError):
    def __init__(self, exception=None):
        self._parent_exception = exception

    def __repr__(self):
        if self._parent_exception:
            return '{0.__class__.__name__}: {0._parent_exception!r}'.format(self)


class ReadOnlyError(ModbusDriverError, IOError):
    def __init__(self, key):
        super().__init__('%s is read-only' % key)


class WriteOnlyError(ModbusDriverError, IOError):
    def __init__(self, key):
        super().__init__('%s is write-only' % key)


class ModbusDriver(AbstractDriver):
    def __init__(self, config):

        self.config = config

        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port"))
        self.target_nodeid = '.'.split(self.target_address)[-1]     # On MFE100, nodeid is always the last byte of his IP address

        self.back = ModbusBackend(self.target_address, self.target_port,
                                  self.target_nodeid)

        self.netdata_map = MicroflexE100Map
        self._prev_data = {}

        self.connected = None

        self.frontend = DriverFrontend()

    @retry(ModbusDriverError, 5, 5, 2)
    def connect(self):
        try:
            if not self.back.connect():
                self.connected = False
                raise ModbusDriverError('Failed to connect {0}:{1}'.format(
                    self.target_address, self.target_port))
            self.connected = True
        except ModbusBackendError as e:
            raise ModbusDriverError('Failed to connect {0}:{1}: {2}'.format(
                self.target_address, self.target_port, e))

    def exit(self):
        self['command:enable'] = False

        self.back.close()

    def get_attribute_map(self):
        attr_map = {}
        for a, p in self.netdata_map.items():
            if isinstance(p, dict):
                for sa, sp in p.items():
                    attr_map.update({'{}:{}'.format(a, sa): (sp.vtype, sp.mode,)})
            else:
                attr_map.update({a: (p.vtype, p.mode,)})

        return attr_map

    def send_default_values(self):
        for key in self.frontend.DEFAULTS_KEYS:
            self[key] = self.frontend[key]

    def _get_value(self, ndk, key):
        nd, st, vt, md = ndk.netdata, ndk.start, ndk.vtype, ndk.mode

        if 'r' not in md:
            raise ReadOnlyError(key)

        try:
            res = self.back.read_netdata(nd.addr, nd.fmt)
            return self.frontend.input_value(key, vt(res[st]))
        except ModbusBackendError as e:
            raise ModbusDriverError('No data returned from backend '
                                    'for {}: {!s}'.format(key, e))

    def __getitem__(self, key):
        try:
            if len(key.split(':')) == 2:
                seckey, subkey = key.split(':')
            else:
                seckey, subkey = key, None

            if seckey not in self.netdata_map:
                raise KeyError(seckey)

            if type(self.netdata_map[seckey]) == dict:
                if subkey:
                    if subkey not in self.netdata_map[seckey]:
                        raise KeyError(subkey)
                    ndk = self.netdata_map[seckey][subkey]
                else:
                    return [(sk, self._get_value(self.netdata_map[seckey][sk], key),)
                            for sk in self.netdata_map[seckey].keys()]
            else:
                ndk = self.netdata_map[seckey]

            return self._get_value(ndk, seckey)
        except Exception as e:
            logging.error('Got exception in {!r}: {!r}'.format(self, e))
            raise ModbusDriverError(e)

    def __setitem__(self, key, value):
        if len(key.split(':')) == 2:
            seckey, subkey = key.split(':')
        else:
            seckey, subkey = key, None

        if seckey not in self.netdata_map:
            raise KeyError('Unable to find {} in netdata map'.format(seckey))

        if type(self.netdata_map[seckey]) == dict and subkey:
            if subkey not in self.netdata_map[seckey]:
                raise KeyError('Unable to find {0} in {1} '
                               'netdata map'.format(subkey, seckey))
            pndk = self.netdata_map[seckey]
            ndk = self.netdata_map[seckey][subkey]
            seclen = len(self.netdata_map[seckey])

            if seckey not in self._prev_data.keys():
                self._prev_data[seckey] = {}

            forget_values = ('cancel', 'reset', 'go', 'set_home', 'go_home', 'stop')
            unique_values = ('control_mode',)
            data = list((-1,) * seclen)

            for k, cndk in pndk.items():
                data[cndk.start] = self._prev_data[seckey].get(k, cndk.vtype(0))
            data[ndk.start] = ndk.vtype(value)

            for k, cndk in pndk.items():
                if k == subkey and subkey in unique_values:
                    try:
                        if ndk.vtype(value) == self._prev_data[seckey][k]:
                            return
                    except KeyError:
                        pass
                elif ndk.start != cndk.start:
                    if k in forget_values:
                        data[cndk.start] = cndk.vtype(0)
                        self._prev_data[seckey][k] = cndk.vtype(0)
                    if k in unique_values:
                        data[cndk.start] = cndk.vtype(0)

            self._prev_data[seckey][subkey] = ndk.vtype(value)
        else:
            ndk = self.netdata_map[seckey]
            data = (self.frontend.output_value(key, ndk.vtype(value)),)

        if 'w' not in ndk.mode:
            raise WriteOnlyError(key)

        return self.back.write_netdata(ndk.netdata.addr, data, ndk.netdata.fmt)

    def __repr__(self):
        return '{0.__class__.__name__}'.format(self)

if __name__ == "__main__":
    c = {
        'target_address': 'localhost',
        'target_port': 501,
    }

    d = ModbusDriver(c)

    try:
        d['velocity'] = True    # This shoud raise ReadOnlyError
        print(d['position_ref'])    # This shoud raise WriteOnlyError
    except ModbusDriverError:
        pass
