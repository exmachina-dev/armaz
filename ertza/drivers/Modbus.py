# -*- coding: utf-8 -*-

from collections import namedtuple

from ertza.drivers.AbstractDriver import AbstractDriver

from ertza.drivers.ModbusBackend import ModbusBackend

from ertza.drivers.Utils import retry


class ModbusDriverError(Exception):
    pass


class ReadOnlyError(ModbusDriverError, IOError):
    def __init__(self, key):
        super().__init__('%s is read-only' % key)


class WriteOnlyError(ModbusDriverError, IOError):
    def __init__(self, key):
        super().__init__('%s is write-only' % key)


class ModbusDriver(AbstractDriver):

    netdata = namedtuple('netdata', ['addr', 'fmt'])
    parameter = namedtuple('parameter', ['netdata', 'start',
                                         'vtype', 'mode'])
    MFNdata = {
        'status':               netdata(0,
                                        'bool,bool,bool,bool,bool,bool'),
        'command':              netdata(1,
                                        'bool,bool,bool,bool,uint:2,uint:1,bool'),
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
        'effort':               netdata(29, 'float:32'),

        'drive_temp':           netdata(30, 'float:32'),
        'dropped_frames':       netdata(31, 'uint:32'),
    }

    MFE100Map = {
        'status': {
            'drive_ready':      parameter(MFNdata['status'], 0, bool, 'r'),
            'drive_enable':     parameter(MFNdata['status'], 1, bool, 'r'),
            'drive_input':      parameter(MFNdata['status'], 2, bool, 'r'),
            'motor_brake':      parameter(MFNdata['status'], 3, bool, 'r'),
            'motor_temp':       parameter(MFNdata['status'], 4, bool, 'r'),
            'timeout':          parameter(MFNdata['status'], 5, bool, 'r'),
        },

        'command': {
            'enable':           parameter(MFNdata['command'], 0, bool, 'w'),
            'cancel':           parameter(MFNdata['command'], 1, bool, 'w'),
            'clear_errors':     parameter(MFNdata['command'], 2, bool, 'w'),
            'reset':            parameter(MFNdata['command'], 3, bool, 'w'),
            'control_mode':     parameter(MFNdata['command'], 4, int, 'w'),
            'move_mode':        parameter(MFNdata['command'], 5, int, 'w'),
            'go':               parameter(MFNdata['command'], 6, bool, 'w'),
        },

        'error_code':       parameter(MFNdata['error_code'], 0, int, 'r'),
        'jog':              parameter(MFNdata['jog'], 0, float, 'rw'),
        'torque_ref':       parameter(MFNdata['torque_ref'], 0, float, 'rw'),
        'velocity_ref':     parameter(MFNdata['velocity_ref'], 0, float, 'rw'),
        'position_ref':     parameter(MFNdata['velocity_ref'], 0, float, 'w'),
        'torque_rise_time': parameter(MFNdata['torque_rise_time'], 0, float, 'rw'),
        'torque_fall_time': parameter(MFNdata['torque_fall_time'], 0, float, 'rw'),
        'acceleration':     parameter(MFNdata['acceleration'], 0, float, 'rw'),
        'deceleration':     parameter(MFNdata['deceleration'], 0, float, 'rw'),

        'velocity':         parameter(MFNdata['velocity'], 0, float, 'r'),
        'position':         parameter(MFNdata['position'], 0, float, 'r'),
        'position_target':  parameter(MFNdata['position_target'], 0, float, 'r'),
        'position_remaining':
        parameter(MFNdata['position_remaining'], 0, float, 'r'),
        'encoder_ticks':    parameter(MFNdata['encoder_ticks'], 0, float, 'r'),
        'encoder_velocity': parameter(MFNdata['encoder_velocity'], 0, float, 'r'),
        'velocity_error':   parameter(MFNdata['velocity_error'], 0, float, 'r'),
        'follow_error':     parameter(MFNdata['follow_error'], 0, float, 'r'),
        'effort':           parameter(MFNdata['effort'], 0, float, 'r'),

        'drive_temp':       parameter(MFNdata['drive_temp'], 0, int, 'r'),
        'dropped_frames':   parameter(MFNdata['dropped_frames'], 0, int, 'r'),
    }

    def __init__(self, config):

        self.target_address = config.get("target_address")
        self.target_port = int(config.get("target_port"))
        self.target_nodeid = '.'.split(self.target_address)[-1]     # On MFE100, nodeid is always the last byte of his IP address

        self.back = ModbusBackend(self.target_address, self.target_port,
                                  self.target_nodeid)

        self.netdata_map = ModbusDriver.MFE100Map

    @retry(ModbusDriverError, 5, 5, 2)
    def connect(self):
        if not self.back.connect():
            raise ModbusDriverError(
                "Failed to connect %s:%i" % (self.target_address,
                                             self.target_port))

    def exit(self):
        self.back.close()

    def __getitem__(self, key):
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
                ret = list()
                for sk in self.netdata_map[seckey].keys():
                    ret.append((
                        sk, self._get_value(self.netdata_map[seckey][sk]),))

                return ret
        else:
            ndk = self.netdata_map[seckey]

        return self._get_value(ndk)

    def __setitem__(self, key, value):
        if key not in self.netdata_map:
            raise KeyError

        if 'w' not in self.netdata_map[key].mode:
            raise WriteOnlyError(key)

    def _get_value(self, ndk):
        nd, st, vt, md = ndk.netdata, ndk.start, ndk.vtype, ndk.mode

        if 'r' not in md:
            raise ReadOnlyError

        res = self.back.read_netdata(nd.addr, nd.fmt)

        return vt(res[st])

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
