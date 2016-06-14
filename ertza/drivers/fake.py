# -*- coding: utf-8 -*-

import logging
from collections import namedtuple

from .abstract_driver import AbstractDriver, AbstractDriverError


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


class FakeDriverFrontend(object):

    def load_frontend_config(self, config):
        self.frontend_config = config

        self.gearbox_ratio = (
            self._safe_config_get("gearbox_input_coefficient", float, 1) /
            self._safe_config_get("gearbox_output_coefficient", float, 1))

        self.torque_constant = self._safe_config_get("torque_constant", float, 1)  # in Nm/A
        self.drive_rated_current = self._safe_config_get("drive_rated_current", float, 1)  # in A

        # Limits
        self.max_velocity = self._safe_config_get("max_velocity", float, 1)     # in rpm (motor side)
        self.max_acceleration = self._safe_config_get("max_acceleration", float, 1)
        self.max_deceleration = self._safe_config_get("max_deceleration", float, 1)

        self.min_torque_rise_time = self._safe_config_get("min_torque_rise_time", float, 5000)
        self.min_torque_fall_time = self._safe_config_get("min_torque_fall_time", float, 5000)

        # Actual values
        self.acceleration = self._safe_config_get("acceleration", float, 1)
        self.deceleration = self._safe_config_get("deceleration", float, 1)

        self.torque_rise_time = self._safe_config_get("torque_rise_time", float, 5000)
        self.torque_fall_time = self._safe_config_get("torque_fall_time", float, 5000)

        # Application parameters
        self.application_coeff = self._safe_config_get('application_coefficient', float, 1)
        self.invert = self._safe_config_get('invert', bool, False)
        self.acceleration_time_mode = self._safe_config_get('acceleration_time_mode', bool, False)

        self.custom_max_velocity = self._safe_config_get("custom_max_velocity", float)  # in rpm (application side)
        self.custom_max_acceleration = self._safe_config_get("custom_max_acceleration", float)
        self.custom_max_deceleration = self._safe_config_get("custom_max_deceleration", float)

        self.custom_max_position = self._safe_config_get("custom_max_position", float)
        self.custom_min_position = self._safe_config_get("custom_min_position", float)

    def init_startup_mode(self):
        if not hasattr(self, 'frontend_config'):
            raise AttributeError('Config not found')

    def enable_drive(self):
        self['jog'] = 0
        self['torque_ref'] = 0
        self['velocity_ref'] = 0
        self['command:enable'] = True

    def disable_drive(self):
        self['jog'] = 0
        self['torque_ref'] = 0
        self['velocity_ref'] = 0
        self['command:enable'] = False

    def reset_drive(self):
        self['command:reset'] = False
        self['command:reset'] = True

    def clear_errors(self):
        self['command:clear_errors'] = False
        self['command:clear_errors'] = True

    def cancel(self):
        self['command:cancel'] = False
        self['command:cancel'] = True

    def set_mode(self, mode):
        if 'torque' == mode:
            self['torque_ref'] = 0
            self['velocity_ref'] = 0
            self['command:control_mode'] = 1
        elif 'velocity' == mode:
            self['torque_ref'] = 0
            self['velocity_ref'] = 0
            self['command:control_mode'] = 2
        elif 'position' == mode:
            self['torque_ref'] = 0
            self['velocity_ref'] = 0
            self['command:control_mode'] = 3
        elif 'enhanced_torque' == mode:
            self['torque_ref'] = 0
            self['velocity_ref'] = 0
            self['command:control_mode'] = 4
        else:
            raise ValueError('Unrecognized mode: {}'.format(mode))

        return mode

    def set_velocity(self, v):
        self['velocity_ref'] = v if not self.invert else -v

        return v

    def set_torque_time(self, rt=None, ft=None):
        if rt is None:
            rt, ft = self.torque_rise_time, self.torque_fall_time
        elif ft is None:
            ft = rt

        if rt < self.min_torque_rise_time:
            raise ValueError('Torque rise time is too small: {} vs {}'.format(
                rt, self.min_torque_rise_time))
        elif ft < self.min_torque_fall_time:
            raise ValueError('Torque fall time is too small: {} vs {}'.format(
                ft, self.min_torque_fall_time))

        self['torque_rise_time'] = rt
        self['torque_fall_time'] = ft

        return rt, ft

    def set_acceleration(self, acc=None, decc=None):
        if acc is None:
            acc, dec = self.acceleration, self.deceleration
        elif dec is None:
            dec = acc

        if acc > self.max_acceleration:
            raise ValueError('Acceleration is too big: {} vs {}'.format(
                acc, self.max_acceleration))
        elif dec > self.max_deceleration:
            raise ValueError('Deceleration is too big: {} vs {}'.format(
                dec, self.max_deceleration))

        self['acceleration'] = dec
        self['deceleration'] = acc

        return acc, dec

    def send_default_values(self):
        self['acceleration'] = self.acceleration
        self['deceleration'] = self.deceleration
        self['torque_rise_time'] = self.torque_rise_time
        self['torque_fall_time'] = self.torque_fall_time

    def _output_value_limit(self, key, value):
        if 'acceleration' == key:
            return value if value < self.max_acceleration else self.max_acceleration
        elif 'deceleration' == key:
            return value if value < self.max_deceleration else self.max_deceleration
        elif 'torque_rise_time' == key:
            return value if value > self.min_torque_rise_time else self.min_torque_rise_time
        elif 'torque_fall_time' == key:
            return value if value > self.min_torque_fall_time else self.min_torque_fall_time
        elif 'velocity_ref' == key:
            value = value if value < self.max_velocity else self.max_velocity
            value = value if value > -self.max_velocity else -self.max_velocity

        return value

    def _output_value_coefficient(self, key, value):
        if key in ('velocity_ref', 'position_ref',):
            if self.custom_max_velocity is not None and key == 'velocity_ref':
                value = value if value < self.custom_max_velocity else self.custom_max_velocity
                value = value if value > -self.custom_max_velocity else -self.custom_max_velocity
            elif key == 'position_ref':
                if self.custom_max_position is not None:
                    value = value if value < self.custom_max_position else self.custom_max_position
                if self.custom_min_position is not None:
                    value = value if value > self.custom_min_position else self.custom_min_position

            value = value * -1 if not self.invert else value
            value /= self.gearbox_ratio
            value *= self.application_coeff
        elif key in ('acceleration', 'deceleration',):
            if self.custom_max_acceleration is not None and key == 'acceleration':
                value = value if value < self.custom_max_acceleration else self.custom_max_acceleration
            if self.custom_max_deceleration is not None and key == 'deceleration':
                value = value if value < self.custom_max_deceleration else self.custom_max_deceleration

            value /= self.gearbox_ratio
            value *= self.application_coeff
            if self.acceleration_time_mode:
                value = (self.max_velocity / self.gearbox_ratio * self.application_coeff) / value
        elif key in ('torque_ref'):
            value = value * -1 if not self.invert else value
            value *= self.gearbox_ratio
            value /= self.torque_constant
            value /= self.drive_rated_current
            value *= 100

        return value

    def _output_value(self, key, value):
        return self._output_value_limit(key, self._output_value_coefficient(key, value))

    def _input_value_coefficient(self, key, value):
        if key in ('velocity_ref', 'velocity',
                   'position_ref', 'position', 'position_target', 'position_remaining',):
            value /= self.application_coeff
            value *= self.gearbox_ratio
        if key in ('acceleration', 'deceleration',):
            value *= self.gearbox_ratio
            value /= self.application_coeff
            if self.acceleration_time_mode:
                value = (self.max_velocity / self.gearbox_ratio * self.application_coeff) / value
        elif key in ('torque_ref'):
            value /= 100
            value *= self.drive_rated_current
            value *= self.torque_constant
            value /= self.gearbox_ratio
            value = value * -1 if not self.invert else value
        elif key in ('torque'):
            value /= self.gearbox_ratio
            value = value * -1 if not self.invert else value
        elif key in ('current_ratio'):
            value = value * -1 if not self.invert else value

        return value

    def _input_value(self, key, value):
        return self._input_value_coefficient(key, value)

    def _safe_config_get(self, key, vtype=None, fallback=None):
        try:
            if vtype:
                if vtype == bool:
                    return True if self.frontend_config[key] == 'True' else False
                return vtype(self.frontend_config[key])
            else:
                return self.frontend_config[key]
        except KeyError:
            return fallback


class FakeDriver(AbstractDriver, FakeDriverFrontend):

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

        self.netdata_map = FakeDriver.MFE100Map
        self._prev_data = {}

        self.connected = None

        self.fake_data = {}

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
            data = (self._output_value(key, ndk.vtype(value)),)

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

        return self._input_value(key, vt(res[st]))

    def write_fake_data(self, addr, data, fmt=None):
        self.fake_data[addr] = data

    def read_fake_data(self, addr, fmt=None):
        try:
            return self.fake_data[addr]
        except KeyError:
            return None
