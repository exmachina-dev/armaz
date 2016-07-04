# -*- coding: utf-8 -*-

import logging

from ..abstract_driver import AbstractDriver, AbstractDriverError
from ..frontend import DriverFrontend
from ..netdata_maps import MicroflexE100Map

logging = logging.getLogger('ertza.drivers.fake')


class FakeDriverError(AbstractDriverError):
    def __init__(self, exception=None):
        self._parent_exception = exception

    def __repr__(self):
        if self._parent_exception:
            return '{0.__class__.__name__}: {0._parent_exception!r}'.format(self)


class ReadOnlyError(FakeDriverError, IOError):
    def __init__(self, key):
        super().__init__('%s is read-only' % key)


class WriteOnlyError(FakeDriverError, IOError):
    def __init__(self, key):
        super().__init__('%s is write-only' % key)


class FakeDriver(AbstractDriver):
    def __init__(self, config):

        self.config = config

        self.netdata_map = MicroflexE100Map
        self._prev_data = {}

        self.connected = None

        self.fake_data = {}

        self.frontend = DriverFrontend()

    def connect(self):
        if not self.connected:
            self.connected = True
        self.connected = True

    def exit(self):
        self['command:enable'] = False

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
            try:
                self[key] = self.frontend[key]
            except KeyError as e:
                logging.error('{!s}'.format(e))

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
                    if subkey not in self.netdata_map:
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
            raise FakeDriverError(e)

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
            ndk = self.netdata_map[seckey][subkey]
            seclen = len(self.netdata_map[seckey])
            if seckey not in self._prev_data.keys():
                data = list((0,) * seclen)
                data[ndk.start] = ndk.vtype(value)
            else:
                pdata = list(self._prev_data[seckey])

                forget_values = (0, 1, 4, 6,)
                unique_values = (3,)
                data = list((-1,) * seclen)
                data[ndk.start] = ndk.vtype(value)
                for i, pvalue in enumerate(pdata):
                    if ndk.start == i and ndk.start in unique_values:
                        if data[ndk.start] == pvalue:
                            return
                    elif ndk.start != i:
                        if i in forget_values:
                            data[i] = 0
                        else:
                            data[i] = pvalue

            self._prev_data[seckey] = data
        else:
            ndk = self.netdata_map[seckey]
            data = (self.frontend._output_value(key, ndk.vtype(value)),)

        if 'w' not in ndk.mode:
            raise WriteOnlyError(key)

        return self.write_fake_data(ndk.netdata.addr, data)

    def _get_value(self, ndk, key):
        nd, st, vt, md = ndk.netdata, ndk.start, ndk.vtype, ndk.mode

        if 'r' not in md:
            raise ReadOnlyError(key)

        res = self.read_fake_data(nd.addr, nd.fmt)
        if not res:
            return

        return self.frontend._input_value(key, vt(res[st]))

    def write_fake_data(self, addr, data, fmt=None):
        self.fake_data[addr] = data

    def read_fake_data(self, addr, fmt=None):
        try:
            return self.fake_data[addr]
        except KeyError:
            return None
