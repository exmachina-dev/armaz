# -*- coding: utf-8 -*-

import logging
from collections import namedtuple

from ertza.drivers.AbstractDriver import AbstractDriver, AbstractDriverError

from ertza.drivers.ModbusBackend import ModbusBackend, ModbusBackendError
from ertza.drivers.ModbusFrontend import ModbusDriverFrontend

from ertza.drivers.Utils import retry


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


class ModbusDriver(AbstractDriver, ModbusDriverFrontend):

    netdata = namedtuple('netdata', ['addr', 'fmt'])
    parameter = namedtuple('parameter', ['netdata', 'start',
                                         'vtype', 'mode'])
    MFNdata = {
        'status':               netdata(0, 'pad:24,bool,bool,bool,bool,'
                                        'bool,bool,bool,bool'),
        'command':              netdata(1, 'pad:21,bool,bool,bool,uint:1,uint:3,'
                                        'bool,bool,bool,bool'),
        'error_code':           netdata(2, 'uint:32'),
        'jog':                  netdata(3, 'float:32'),
        'torque_ref':           netdata(4, 'float:32'),
        'velocity_ref':         netdata(5, 'float:32'),
        'position_ref':         netdata(6, 'float:32'),

        'torque_rise_time':     netdata(10, 'float:32'),
        'torque_fall_time':     netdata(11, 'float:32'),
        'acceleration':         netdata(12, 'float:32'),
        'deceleration':         netdata(13, 'float:32'),

        'velocity':             netdata(21, 'float:32'),
        'position':             netdata(22, 'float:32'),
        'position_target':      netdata(23, 'float:32'),
        'position_remaining':   netdata(24, 'float:32'),
        'encoder_ticks':        netdata(25, 'float:32'),
        'encoder_velocity':     netdata(26, 'float:32'),
        'velocity_error':       netdata(27, 'float:32'),
        'follow_error':         netdata(28, 'float:32'),
        'torque':               netdata(29, 'float:32'),
        'current_ratio':        netdata(30, 'float:32'),
        'effort':               netdata(31, 'float:32'),

        'drive_temp':           netdata(50, 'float:32'),
        'dropped_frames':       netdata(51, 'uint:32'),
    }

    p = parameter

    MFE100Map = {
        'status': {
            'drive_ready':      p(MFNdata['status'], 7, bool, 'r'),
            'drive_enable':     p(MFNdata['status'], 6, bool, 'r'),
            'drive_input':      p(MFNdata['status'], 5, bool, 'r'),
            'motor_brake':      p(MFNdata['status'], 4, bool, 'r'),
            'motor_temp':       p(MFNdata['status'], 3, bool, 'r'),
            'timeout':          p(MFNdata['status'], 2, bool, 'r'),
        },

        'command': {
            'enable':           p(MFNdata['command'], 8, bool, 'w'),
            'cancel':           p(MFNdata['command'], 7, bool, 'w'),
            'clear_errors':     p(MFNdata['command'], 6, bool, 'w'),
            'reset':            p(MFNdata['command'], 5, bool, 'w'),
            'control_mode':     p(MFNdata['command'], 4, int, 'w'),
            'move_mode':        p(MFNdata['command'], 3, int, 'w'),
            'go':               p(MFNdata['command'], 2, bool, 'w'),
            'set_home':         p(MFNdata['command'], 1, bool, 'w'),
            'stop':             p(MFNdata['command'], 0, bool, 'w'),
        },

        'error_code':           p(MFNdata['error_code'], 0, int, 'r'),
        'jog':                  p(MFNdata['jog'], 0, float, 'rw'),
        'torque_ref':           p(MFNdata['torque_ref'], 0, float, 'rw'),
        'velocity_ref':         p(MFNdata['velocity_ref'], 0, float, 'rw'),
        'position_ref':         p(MFNdata['position_ref'], 0, float, 'w'),
        'torque_rise_time':     p(MFNdata['torque_rise_time'], 0, float, 'rw'),
        'torque_fall_time':     p(MFNdata['torque_fall_time'], 0, float, 'rw'),
        'acceleration':         p(MFNdata['acceleration'], 0, float, 'rw'),
        'deceleration':         p(MFNdata['deceleration'], 0, float, 'rw'),

        'velocity':             p(MFNdata['velocity'], 0, float, 'r'),
        'position':             p(MFNdata['position'], 0, float, 'r'),
        'position_target':      p(MFNdata['position_target'], 0, float, 'r'),
        'position_remaining':   p(MFNdata['position_remaining'], 0, float, 'r'),
        'encoder_ticks':        p(MFNdata['encoder_ticks'], 0, float, 'r'),
        'encoder_velocity':     p(MFNdata['encoder_velocity'], 0, float, 'r'),
        'velocity_error':       p(MFNdata['velocity_error'], 0, float, 'r'),
        'follow_error':         p(MFNdata['follow_error'], 0, float, 'r'),
        'torque':               p(MFNdata['torque'], 0, float, 'r'),
        'current_ratio':        p(MFNdata['current_ratio'], 0, float, 'r'),
        'effort':               p(MFNdata['effort'], 0, float, 'r'),

        'drive_temp':           p(MFNdata['drive_temp'], 0, float, 'r'),
        'dropped_frames':       p(MFNdata['dropped_frames'], 0, int, 'r'),
    }

    del p

    def __init__(self, config):

        self.config = config

        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port"))
        self.target_nodeid = '.'.split(self.target_address)[-1]     # On MFE100, nodeid is always the last byte of his IP address

        self.back = ModbusBackend(self.target_address, self.target_port,
                                  self.target_nodeid)

        self.netdata_map = ModbusDriver.MFE100Map
        self._prev_data = {}

        self.connected = None

    @retry(ModbusDriverError, 5, 5, 2)
    def connect(self):
        if not self.back.connect():
            self.connected = False
            raise ModbusDriverError(
                "Failed to connect %s:%i" % (self.target_address,
                                             self.target_port))
        self.connected = True

    def exit(self):
        self['command:enable'] = False

        self.back.close()

    def get_attribute_map(self):
        attr_map = {}
        for a, p in self.netdata_map.items():
            if isinstance(p, dict):
                for sa, sp in p.items():
                    attr_map.update({'{}:{}'.format(a, sa): (sp.vtype, sp.mode,),})
            else:
                attr_map.update({a: (p.vtype, p.mode,),})

        return attr_map

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
            data = (self._output_value(key, ndk.vtype(value)),)

        if 'w' not in ndk.mode:
            raise WriteOnlyError(key)

        return self.back.write_netdata(ndk.netdata.addr, data, ndk.netdata.fmt)

    def _get_value(self, ndk, key):
        nd, st, vt, md = ndk.netdata, ndk.start, ndk.vtype, ndk.mode

        if 'r' not in md:
            raise ReadOnlyError(key)

        try:
            res = self.back.read_netdata(nd.addr, nd.fmt)
            return self._input_value(key, vt(res[st]))
        except ModbusBackendError as e:
            raise ModbusDriverError('No data returned from backend '
                                    'for {}: {!s}'.format(key, e))

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
