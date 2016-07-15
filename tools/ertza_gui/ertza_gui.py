#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PySide import QtGui
from PySide import QtCore
import functools
import collections

import liblo as lo
import logging as lg

from ertza_widgets import SwitchWidget, PushButton, UpdatableTableWidget

VERSION = '0.0.1'


class EmbeddedLogHandler(lg.Handler):

    def __init__(self, widget):
        super().__init__()
        self.setLevel(lg.DEBUG)

        self.widget = widget

        self.color = {
            "INFO": QtGui.QColor(0, 127, 0),
            "DEBUG": QtGui.QColor(127, 127, 127),
            "WARNING": QtGui.QColor(127, 127, 0),
            "ERROR": QtGui.QColor(127, 0, 0),
            "CRITICAL": QtGui.QColor(255, 0, 0),
        }
        super().__init__()

    def emit(self, record):
        msg = self.format(record) + '\n'

        self.widget.setTextColor(self.color[record.levelname])

        self.widget.moveCursor(QtGui.QTextCursor.End)
        self.widget.insertPlainText(msg)


class OrderedDictTrigger(QtCore.QObject):
    signal = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        self._values = collections.OrderedDict()
        self._vtypes = {}
        self._vunits = {}

        QtCore.QObject.__init__(self, *args, **kwargs)

    def get_type(self, key):
        return self._vtypes[key]

    def get_unit(self, key):
        return self._vunits[key]

    def __setitem__(self, key, value):
        vl = vt = vu = None

        if isinstance(value, (tuple, list)):
            if len(value) == 1:
                vt, = value
            elif len(value) == 2:
                vt, vu = value
            elif len(value) == 3:
                vl, vt, vu = value
        else:
            vl = value

        self._values.__setitem__(key, vl)
        self._vtypes[key] = vt
        self._vunits[key] = vu
        self.signal.emit((key, vl, vt, vu))

    def __getitem__(self, key):
        return self._values[key]

    def __len__(self):
        return len(self.__values)

    def keys(self):
        return self._values.keys()


console_logger = lg.StreamHandler()
console_formatter = lg.Formatter(
    '%(asctime)s %(name)-36s %(levelname)-8s %(message)s',
    datefmt='%Y%m%d %H:%M:%S')

embedded_formatter = lg.Formatter(
    '%(asctime)s %(name)-20s %(levelname)-7s %(message)s',
    datefmt='%d %H:%M:%S')

logging = lg.getLogger('ertza-gui')
logging.addHandler(console_logger)
console_logger.setFormatter(console_formatter)

logging.setLevel(lg.DEBUG)


class ErtzaOSCServer(lo.ServerThread):
    def __init__(self, to, *args, **kwargs):
        self.to = to
        super(ErtzaOSCServer, self).__init__(*args, **kwargs)

    def reply(self, default_path, sender, *args, **kwargs):
        if kwargs and 'merge' in kwargs.keys():
            kwargs['merge'] = True
        else:
            kwargs['merge'] = False

        try:
            if type(args[0]) == str and args[0][0] == '/':
                args = list(args)
                _msg = lo.Message(args.pop(0), *args)
            elif len(args) >= 2 and kwargs['merge']:
                args = list(args)
                path = args.pop(0)
                _msg = lo.Message(default_path+'/'+path, *args)
            else:
                _msg = lo.Message(default_path, *args)
        except (TypeError, KeyError, IndexError):
            _msg = lo.Message(default_path, *args)
        self.send(sender, _msg)
        return _msg

    @lo.make_method('/alive', None)
    def online_cb(self, path, args, types, sender):
        logging.info('{} is online, listening on {}'.format(*args))
        if self.to.master.target_addr.text == args[1]:
            self.to.request_status()

    @lo.make_method(None, None)
    def default_cb(self, path, args, types, sender):
        self.to.handle(sender.get_hostname(), path, *args)


class ErtzaActions(object):
    REFRESH_VALUES = ('disable', '500 ms', '1 s', '2 s', '5 s')

    def __init__(self, master):
        self.master = master
        self.connected = False
        self.osc_server = None

        self.status = OrderedDictTrigger()
        self.profile_options = OrderedDictTrigger()

        self._config = {}

    def load_defaults(self):
        self.master.target_addr.setText('10.0.0.0')
        self.master.target_port.setValue(6969)
        self.master.listen_port.setValue(6969)

        logging.info('Welcome to Ertza debug GUI.')
        logging.info('Version : %s' % (VERSION,))

    def handle(self, sender, path, *args):
        """
        OSC commands loaded: /log/to /config/profile/load /machine/get /config/set /machine/slave/add /config/save /config/profile/save /log/level /slave/ping /slave/register/ok /config/profile/dump /machine/set /slave/set/error /slave/free /machine/slave/remove /slave/get /slave/set /help/list /drive/get /config/get /config/profile/list_options /slave/get/error /slave/register /config/profile/unload /version /machine/slaves /drive/set /slave/set/ok /slave/ping/ok /machine/slave/mode /slave/get/ok /identify /config/profile/set
        """

        if '/error' in path:
            logging.error('Error in response: {} {}'.format(path, ' '.join(args)))
            return

        if '/identify' in path:
            # Ignore identify requests
            return

        if '/ok' in path:
            if self.config_get('debug', False):
                a = ' '.join(map(repr, args))
                logging.debug('From {}: {} {}'.format(sender, path, a))
            if '/machine/get' in path:
                k, v, = args
                self.status[k] = v
            elif '/config/get' in path:
                k, v, = args
                self.profile_options[k] = v
            elif '/identify' in path:
                logging.info('Machine {} found at {}'.format(*args))
            elif '/version' in path:
                logging.info('Version for {}: {}'.format(sender, *args))

        elif '/config/profile/list_options' in path:
            if len(args) == 2:
                k, v = args
                self.profile_options[k] = (v,)
            elif len(args) == 3:
                k, v, vt = args
                self.profile_options[k] = (v, vt)
        elif '/config/profile/dump' in path:
            p, k, v = args
            self.profile_options[k] = v
        elif '/config/profile/list' in path:
            self.master.stp_profile_list.addItem(args[0])
        else:
            logging.warn('Unexpected response: {} {}'.format(path, ' '.join([str(a) for a in args])))

    def connect(self):
        target_addr = self.config_get('target_addr', None)
        target_port = self.config_get('target_port', 6969)

        if self.osc_server:
            self.osc_server = None

        self.launch_server()

        logging.info('Setting target to {}:{}'.format(target_addr, target_port))
        self.target = lo.Address(target_addr, target_port)
        self.connected = True

        self.request_version()

    def launch_server(self):
        listen_port = self.config_get('listen_port', 6969)

        logging.info('Starting server on {}'.format(listen_port))
        self.osc_server = ErtzaOSCServer(self, listen_port, lo.UDP)
        self.osc_server.start()

    def close(self):
        self.stop()
        root.destroy()

    def send(self, path, *args, **kwargs):
        try:
            if 'target' in kwargs:
                if not self.osc_server:
                    self.launch_server()

                return self.osc_server.reply(None, kwargs.get('target'), path, *args)
            if self.connected:
                return self.osc_server.reply(None, self.target, path, *args)
            else:
                logging.error('Cannot send, not connected')
        except OSError as e:
            logging.error(repr(e))

    def cmd_send(self):
        cmd = self.master.cmd_line.text()
        if not cmd:
            return

        try:
            try:
                cmd, args, = cmd.split(' ')
                if not isinstance(args, tuple):
                    args = (args,)

                self.send(cmd, *args)
                logging.info('Command sent: {} {}'.format(cmd, ' '.join(args)))
            except ValueError:
                self.send(cmd)
                logging.info('Command sent: {}'.format(cmd))
            finally:
                self.master.cmd_line.clear()
        except Exception as e:
            logging.error('Error while sending command: {!r}'.format(e))

    def identify(self):
        t = lo.Address('255.255.255.255', self.config_get('target_port', 6969))
        self.send('/identify', target=t)

    def request_version(self):
        self.send('/version')

    def request_status(self):
        st = (
            'machine:status:drive_ready', 'machine:status:drive_enable',
            'machine:status:drive_input', 'machine:status:motor_brake',
            'machine:status:motor_temp', 'machine:status:timeout',

            'machine:error_code', 'machine:jog',
            'machine:torque_ref', 'machine:velocity_ref',
            'machine:torque_rise_time', 'machine:torque_fall_time',
            'machine:acceleration', 'machine:deceleration',
            'machine:entq_kp', 'machine:entq_kp_vel',
            'machine:entq_ki', 'machine:entq_kd',

            'machine:velocity', 'machine:position',
            'machine:position_target', 'machine:position_remaining',
            'machine:encoder_ticks', 'machine:encoder_velocity',
            'machine:velocity_error', 'machine:follow_error',
            'machine:torque', 'machine:current_ratio',
            'machine:effort',

            'machine:drive_temp', 'machine:dropped_frames',
        )
        for s in st:
            self.send('/machine/get', s)

    def drive_cancel(self):
        self.send('/debug/drive/drive_cancel', 1)

    def drive_clear(self):
        self.send('/debug/drive/clear_errors', 1)

    def stop(self):
        self.speed(0)

    def speed(self, speed=None):
        if speed is not None:
            self.master.ctl_speed.set(speed)
        else:
            speed = self.master.ctl_speed.get()

        self.send('/debug/drive/speed', int(speed))

    def reverse_speed(self):
        speed = self.master.ctl_speed.get()
        self.speed(int(speed * -1))

    def update_status(self):
        self.send('/motor/status')

    def update_field(self, sec, opt, val):
        try:
            self.fields[sec][opt].set(val)
            logging.error('Setting %s.%s to %s' % (sec, opt, val))
        except KeyError:
            logging.error('Unexcepted config %s.%s %s' % (sec, opt, val))
            pass

    def update_device(self, *args):
        pass

    def __setattr__(self, attr, value):
        try:
            super().__setattr__(attr, value)
        except AttributeError:
            if 'set_' == attr[0:4]:
                self._config[attr[4:]] = value
            elif 'isend_' == attr[0:6]:
                self._instant_sender(attr[6:], value)
            else:
                raise AttributeError

    def __getattribute__(self, attr):
        try:
            return super().__getattribute__(attr)
        except AttributeError:
            if 'set_' == attr[0:4]:
                return functools.partial(self._setter, attr[4:])
            elif 'isend_' == attr[0:6]:
                return functools.partial(self._instant_sender, attr[6:])
            elif 'iconf_' == attr[0:6]:
                return functools.partial(self._instant_config, attr[6:])
            elif 'get_' == attr[0:4]:
                return functools.partial(self._getter, attr[4:])
            else:
                raise AttributeError

    def _setter(self, key, value):
        self._config[key] = value

    def _getter(self, key):
        return self._config[key]

    def _instant_sender(self, key, value=1):
        if key.startswith('command_'):
            if 'control_mode' in key:
                value += 1
            self.send('/machine/set', 'machine:command:{}'.format(key[8:]), value)
        else:
            self.send('/machine/set', 'machine:{}'.format(key), value)

    def _instant_config(self, key, *args):
        if key.startswith('profile_'):
            if key in ('profile_load', 'profile_save', 'profile_dump'):
                try:
                    value = self.config_get('profile_name')
                except KeyError:
                    value = None
            elif 'profile_set' in key:
                vkey, value = args
                self.send('/config/profile/{}'.format(key[8:]), vkey, value)
                return
            else:
                try:
                    value = args[0]
                except IndexError:
                    value = None

            if value is not None:
                self.send('/config/profile/{}'.format(key[8:]), value)
            else:
                self.send('/config/profile/{}'.format(key[8:]))
        elif key.startswith('config_'):
            if 'get' in key:
                for k in self.profile_options._values.keys():
                    self.send('/config/get', k)
        else:
            value = args[0]
            self.send('/machine/set', 'machine:{}'.format(key), value)

    def config_get(self, key, fallback=None):
        try:
            return getattr(self, 'get_{}'.format(key))()
        except KeyError:
            if fallback is not None:
                return fallback
            raise


class ErtzaGui(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()
        self.actions = ErtzaActions(self)

        self.create_widgets()

        self.embedded_log_handler = EmbeddedLogHandler(self.log_list)
        self.embedded_log_handler.setFormatter(embedded_formatter)
        logging.addHandler(self.embedded_log_handler)
        self.embedded_log_handler.setLevel(lg.DEBUG)
        logging.setLevel(lg.DEBUG)

        self.actions.load_defaults()

    def create_widgets(self):
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Plastique'))

        self.statusBar().showMessage('Starting…')

        self.setGeometry(500, 900, 250, 150)
        self.setWindowTitle('Ertza GUI')

        main_frame = QtGui.QFrame(self)
        self._main_layout = QtGui.QGridLayout(main_frame)
        self.setCentralWidget(main_frame)

        self._menubar()

        self.show()

        self._device_section()
        self._log_section()
        self._control_section()
        self._config_section()
        self._status_section()

        self.statusBar().showMessage('Ready.')

    def _menubar(self):
        exit_action = QtGui.QAction(QtGui.QIcon.fromTheme('application-exit'), '&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(exit_action)

    def _log_section(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        frame = QtGui.QGroupBox('Log')
        frame.setLayout(grid)

        self.log_list = QtGui.QTextEdit()
        self.cmd_line = QtGui.QLineEdit()

        self.log_list.setReadOnly(True)
        self.log_list.setLineWrapMode(QtGui.QTextEdit.NoWrap)

        self.cmd_line.returnPressed.connect(self.actions.cmd_send)

        grid.addWidget(self.log_list, 0, 0, 9, 0)
        grid.addWidget(self.cmd_line, 9, 0)

        self.centralWidget().layout().addWidget(frame, 0, 1, 1, 2)

    def _control_section(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        frame = QtGui.QGroupBox('Control')
        frame.setLayout(grid)

        ctl_grid = QtGui.QGridLayout()
        ctl_grid.setSpacing(2)
        for i in range(1, 8, 2):
            ctl_grid.setColumnMinimumWidth(i, 10)
        ctl_grid.setColumnStretch(0, 2)
        ctl_grid.setColumnStretch(2, 2)
        ctl_grid.setColumnStretch(4, 2)
        ctl_grid.setColumnStretch(6, 2)
        ctl_frame = QtGui.QFrame()
        ctl_frame.setLayout(ctl_grid)

        self.ctl_enable_but = SwitchWidget()
        self.ctl_cancel_but = PushButton('Drive cancel')
        self.ctl_clear_errors_but = PushButton('Clear errors')
        self.ctl_stop_but = PushButton('Stop')

        self.ctl_cancel_but.color = QtGui.QColor(156, 96, 96)
        self.ctl_stop_but.color = QtGui.QColor(156, 96, 96)

        self.ctl_enable_but.valueChanged.connect(self.actions.isend_command_enable)
        self.ctl_cancel_but.clicked.connect(self.actions.isend_command_cancel)
        self.ctl_clear_errors_but.clicked.connect(self.actions.isend_command_clear_errors)
        self.ctl_stop_but.clicked.connect(self.actions.isend_command_stop)

        ctl_grid.addWidget(QtGui.QLabel('Drive enable'), 0, 0)
        ctl_grid.addWidget(self.ctl_enable_but, 1, 0, 2, 1)
        ctl_grid.addWidget(self.ctl_cancel_but, 1, 2, 2, 1)
        ctl_grid.addWidget(self.ctl_clear_errors_but, 1, 4, 2, 1)
        ctl_grid.addWidget(self.ctl_stop_but, 1, 6, 2, 1)

        ctl_tabs = QtGui.QTabWidget()
        ctl_tabs.currentChanged.connect(self.actions.isend_command_control_mode)

        tq_grid = QtGui.QGridLayout()
        tq_grid.setSpacing(10)

        tq_frame = QtGui.QFrame()
        tq_frame.setLayout(tq_grid)

        self.ctl_torque_ref_input = QtGui.QDoubleSpinBox()
        self.ctl_tq_rise_time_input = QtGui.QDoubleSpinBox()
        self.ctl_tq_fall_time_input = QtGui.QDoubleSpinBox()

        self.ctl_torque_ref_input.valueChanged.connect(self.actions.isend_torque_ref)
        self.ctl_tq_rise_time_input.valueChanged.connect(self.actions.isend_torque_rise_time)
        self.ctl_tq_fall_time_input.valueChanged.connect(self.actions.isend_torque_fall_time)

        self.ctl_torque_ref_input.setRange(-100, 100)
        self.ctl_tq_rise_time_input.setRange(0, 100000)
        self.ctl_tq_fall_time_input.setRange(0, 100000)

        self.ctl_torque_ref_input.setSuffix(' %')
        self.ctl_tq_rise_time_input.setSuffix(' ms')
        self.ctl_tq_fall_time_input.setSuffix(' ms')

        tq_grid.addWidget(QtGui.QLabel('Torque ref'), 0, 0)
        tq_grid.addWidget(self.ctl_torque_ref_input, 0, 1)

        tq_grid.addWidget(QtGui.QLabel('Torque rise time'), 1, 0)
        tq_grid.addWidget(self.ctl_tq_rise_time_input, 1, 1)

        tq_grid.addWidget(QtGui.QLabel('Torque fall time'), 2, 0)
        tq_grid.addWidget(self.ctl_tq_fall_time_input, 2, 1)

        vl_grid = QtGui.QGridLayout()
        vl_grid.setSpacing(10)

        vl_frame = QtGui.QFrame()
        vl_frame.setLayout(vl_grid)

        self.ctl_velocity_ref_input = QtGui.QDoubleSpinBox()
        self.ctl_vl_acceleration_input = QtGui.QDoubleSpinBox()
        self.ctl_vl_deceleration_input = QtGui.QDoubleSpinBox()

        self.ctl_velocity_ref_input.setRange(-100000, 100000)
        self.ctl_vl_acceleration_input.setRange(0, 10000)
        self.ctl_vl_deceleration_input.setRange(0, 10000)

        self.ctl_velocity_ref_input.valueChanged.connect(self.actions.isend_velocity_ref)
        self.ctl_vl_acceleration_input.valueChanged.connect(self.actions.isend_acceleration)
        self.ctl_vl_deceleration_input.valueChanged.connect(self.actions.isend_deceleration)

        self.ctl_velocity_ref_input.setSuffix(' rpm')
        self.ctl_vl_acceleration_input.setSuffix(' ms.s-1')
        self.ctl_vl_deceleration_input.setSuffix(' ms.s-1')

        vl_grid.addWidget(QtGui.QLabel('Velocity ref'), 0, 0)
        vl_grid.addWidget(self.ctl_velocity_ref_input, 0, 1)

        vl_grid.addWidget(QtGui.QLabel('Acceleration'), 1, 0)
        vl_grid.addWidget(self.ctl_vl_acceleration_input, 1, 1)

        vl_grid.addWidget(QtGui.QLabel('Deceleration'), 2, 0)
        vl_grid.addWidget(self.ctl_vl_deceleration_input, 2, 1)

        ps_grid = QtGui.QGridLayout()
        ps_grid.setSpacing(10)

        ps_frame = QtGui.QFrame()
        ps_frame.setLayout(ps_grid)

        self.ctl_ps_go_but = PushButton('GO')
        self.ctl_ps_set_home_but = PushButton('Set home')
        self.ctl_position_ref_input = QtGui.QDoubleSpinBox()
        self.ctl_ps_velocity_input = QtGui.QDoubleSpinBox()
        self.ctl_ps_acceleration_input = QtGui.QDoubleSpinBox()
        self.ctl_ps_deceleration_input = QtGui.QDoubleSpinBox()
        self.ctl_ps_position_mode_input = SwitchWidget()
        self.ctl_ps_move_mode_input = SwitchWidget()

        self.ctl_position_ref_input.setRange(-100000000, 100000000)
        self.ctl_velocity_ref_input.setRange(-100000, 100000)
        self.ctl_vl_acceleration_input.setRange(0, 10000)
        self.ctl_vl_deceleration_input.setRange(0, 10000)
        self.ctl_ps_position_mode_input.choices = ('Absolute', 'Relative')
        self.ctl_ps_position_mode_input.colors = (QtGui.QColor(80, 80, 122), QtGui.QColor(80, 122, 122))
        self.ctl_ps_move_mode_input.choices = ('Cumulative', 'Replace')
        self.ctl_ps_move_mode_input.colors = (QtGui.QColor(80, 80, 122), QtGui.QColor(80, 122, 122))

        self.ctl_ps_go_but.clicked.connect(self.actions.isend_command_go)
        self.ctl_ps_set_home_but.clicked.connect(self.actions.isend_command_set_home)
        self.ctl_position_ref_input.valueChanged.connect(self.actions.isend_position_ref)
        self.ctl_ps_velocity_input.valueChanged.connect(self.actions.isend_velocity_ref)
        self.ctl_ps_acceleration_input.valueChanged.connect(self.actions.isend_acceleration)
        self.ctl_ps_deceleration_input.valueChanged.connect(self.actions.isend_deceleration)

        self.ctl_position_ref_input.setSuffix(' ticks')
        self.ctl_ps_velocity_input.setSuffix(' rpm')
        self.ctl_ps_acceleration_input.setSuffix(' ms.s-1')
        self.ctl_ps_deceleration_input.setSuffix(' ms.s-1')

        ps_grid.addWidget(QtGui.QLabel('Position ref'), 0, 0)
        ps_grid.addWidget(self.ctl_position_ref_input, 0, 1)

        ps_grid.addWidget(self.ctl_ps_go_but, 0, 3)

        ps_grid.addWidget(QtGui.QLabel('Position Mode'), 1, 2)
        ps_grid.addWidget(self.ctl_ps_position_mode_input, 1, 3)

        ps_grid.addWidget(QtGui.QLabel('Move Mode'), 2, 2)
        ps_grid.addWidget(self.ctl_ps_move_mode_input, 2, 3)

        ps_grid.addWidget(self.ctl_ps_set_home_but, 3, 3)

        ps_grid.addWidget(QtGui.QLabel('Velocity'), 1, 0)
        ps_grid.addWidget(self.ctl_ps_velocity_input, 1, 1)

        ps_grid.addWidget(QtGui.QLabel('Acceleration'), 2, 0)
        ps_grid.addWidget(self.ctl_ps_acceleration_input, 2, 1)

        ps_grid.addWidget(QtGui.QLabel('Deceleration'), 3, 0)
        ps_grid.addWidget(self.ctl_ps_deceleration_input, 3, 1)

        et_grid = QtGui.QGridLayout()
        et_grid.setSpacing(10)

        et_frame = QtGui.QFrame()
        et_frame.setLayout(et_grid)

        self.ctl_et_torque_ref_input = QtGui.QDoubleSpinBox()
        self.ctl_et_velocity_ref_input = QtGui.QDoubleSpinBox()
        self.ctl_et_rise_time_input = QtGui.QDoubleSpinBox()
        self.ctl_et_fall_time_input = QtGui.QDoubleSpinBox()

        self.ctl_et_torque_ref_input.valueChanged.connect(self.actions.isend_torque_ref)
        self.ctl_et_velocity_ref_input.valueChanged.connect(self.actions.isend_velocity_ref)
        self.ctl_et_rise_time_input.valueChanged.connect(self.actions.isend_torque_rise_time)
        self.ctl_et_fall_time_input.valueChanged.connect(self.actions.isend_torque_fall_time)

        self.ctl_et_torque_ref_input.setRange(-200, 200)
        self.ctl_et_velocity_ref_input.setRange(-10000, 10000)
        self.ctl_et_rise_time_input.setRange(0, 100000)
        self.ctl_et_fall_time_input.setRange(0, 100000)

        self.ctl_et_torque_ref_input.setSuffix(' %')
        self.ctl_et_velocity_ref_input.setSuffix(' rpm')
        self.ctl_et_rise_time_input.setSuffix(' ms')
        self.ctl_et_fall_time_input.setSuffix(' ms')

        et_grid.addWidget(QtGui.QLabel('Torque ref'), 0, 0)
        et_grid.addWidget(self.ctl_et_torque_ref_input, 0, 1)

        et_grid.addWidget(QtGui.QLabel('Velocity ref'), 1, 0)
        et_grid.addWidget(self.ctl_et_velocity_ref_input, 1, 1)

        et_grid.addWidget(QtGui.QLabel('Torque rise time'), 2, 0)
        et_grid.addWidget(self.ctl_et_rise_time_input, 2, 1)

        et_grid.addWidget(QtGui.QLabel('Torque fall time'), 3, 0)
        et_grid.addWidget(self.ctl_et_fall_time_input, 3, 1)

        ctl_tabs.addTab(tq_frame, '&Torque mode')
        ctl_tabs.addTab(vl_frame, '&Velocity mode')
        ctl_tabs.addTab(ps_frame, '&Position mode')
        ctl_tabs.addTab(et_frame, '&Enhanced Torque mode')

        grid.addWidget(ctl_frame, 0, 0)
        grid.addWidget(ctl_tabs, 1, 0)

        self.centralWidget().layout().addWidget(frame, 1, 0, 1, 2)

    def _device_section(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        frame = QtGui.QGroupBox('Connection')
        frame.setLayout(grid)

        scan_button = PushButton('Scan request')
        self.target_addr = QtGui.QLineEdit()
        self.target_port = QtGui.QSpinBox()
        self.listen_port = QtGui.QSpinBox()
        connect_button = PushButton('Connect')
        debug_checkbox = QtGui.QCheckBox('Debug')

        self.target_port.setRange(0, 99999)
        self.listen_port.setRange(0, 99999)

        scan_button.clicked.connect(self.actions.identify)
        self.target_addr.textEdited.connect(self.actions.set_target_addr)
        self.target_port.valueChanged.connect(self.actions.set_target_port)
        self.listen_port.valueChanged.connect(self.actions.set_listen_port)

        debug_checkbox.stateChanged.connect(self.actions.set_debug)
        connect_button.clicked.connect(self.actions.connect)

        grid.addWidget(scan_button, 0, 1, 1, 4)

        grid.addWidget(QtGui.QLabel('IP Address'), 1, 0)
        grid.addWidget(self.target_addr, 1, 1, 1, 3,)

        grid.addWidget(QtGui.QLabel(':'), 1, 4)
        grid.addWidget(self.target_port, 1, 5)

        grid.addWidget(QtGui.QLabel('Listen Port'), 2, 0)
        grid.addWidget(self.listen_port, 2, 1)

        grid.addWidget(debug_checkbox, 2, 5)

        grid.addWidget(connect_button, 3, 1, 1, 4)

        self.centralWidget().layout().addWidget(frame, 0, 0)

    def _config_section(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        frame = QtGui.QGroupBox('Setup')
        frame.setLayout(grid)

        stp_tabs = QtGui.QTabWidget()

        pfl_grid = QtGui.QGridLayout()
        pfl_grid.setSpacing(10)

        pfl_frame = QtGui.QFrame()
        pfl_frame.setLayout(pfl_grid)

        self.stp_profile_list = QtGui.QComboBox()
        self.stp_refresh_pfl_but = PushButton('Refresh profile list')
        self.stp_load_pfl_but = PushButton('Load profile')
        self.stp_unload_pfl_but = PushButton('Unload profile')
        self.stp_save_pfl_but = PushButton('Save profile')
        self.stp_refresh_opt_but = PushButton('Get option list')
        self.stp_dump_profile_but = PushButton('Dump profile')
        self.stp_get_actual_values_but = PushButton('Get values')

        stp_options_box = QtGui.QGroupBox('Options')
        stp_options_grid = QtGui.QGridLayout()
        stp_options_box.setLayout(stp_options_grid)
        self.stp_profile_options_table = UpdatableTableWidget(0, 3)
        self.stp_profile_options_table.setHorizontalHeaderLabels(('Key', 'Value', 'Unit'))

        self.stp_unload_pfl_but.color = QtGui.QColor(156, 96, 96)
        self.stp_profile_list.setEditable(True)

        self.stp_profile_list.currentIndexChanged.connect(self.actions.set_profile_id)
        self.stp_profile_list.editTextChanged.connect(self.actions.set_profile_name)

        self.stp_refresh_pfl_but.clicked.connect(self.actions.iconf_profile_list)
        self.stp_refresh_pfl_but.clicked.connect(self.stp_profile_list.clear)

        self.stp_load_pfl_but.clicked.connect(self.actions.iconf_profile_load)
        self.stp_unload_pfl_but.clicked.connect(self.actions.iconf_profile_unload)
        self.stp_save_pfl_but.clicked.connect(self.actions.iconf_profile_save)

        self.stp_refresh_opt_but.clicked.connect(self.actions.iconf_profile_list_options)

        self.stp_dump_profile_but.clicked.connect(self.actions.iconf_profile_dump)
        self.stp_dump_profile_but.clicked.connect(self.stp_profile_options_table.clear_values)

        self.stp_get_actual_values_but.clicked.connect(self.actions.iconf_config_get)

        self.actions.profile_options.signal.connect(self.stp_profile_options_table.update_content)

        self.stp_profile_options_table.itemChanged.connect(self.stp_profile_options_table.update_value)
        self.stp_profile_options_table.valueChanged.connect(self.actions.iconf_profile_set)

        pfl_grid.addWidget(self.stp_profile_list, 0, 0, 1, 2)
        pfl_grid.addWidget(self.stp_refresh_pfl_but, 0, 2)
        pfl_grid.addWidget(self.stp_load_pfl_but, 1, 0)
        pfl_grid.addWidget(self.stp_unload_pfl_but, 1, 1)
        pfl_grid.addWidget(self.stp_save_pfl_but, 1, 2)
        pfl_grid.addWidget(self.stp_refresh_opt_but, 2, 0)
        pfl_grid.addWidget(self.stp_dump_profile_but, 2, 1)
        pfl_grid.addWidget(self.stp_get_actual_values_but, 2, 2)
        pfl_grid.addWidget(stp_options_box, 3, 0, 10, 0)

        stp_options_grid.addWidget(self.stp_profile_options_table, 0, 0)

        # Config tab
        cnf_grid = QtGui.QGridLayout()
        cnf_grid.setSpacing(10)

        cnf_frame = QtGui.QFrame()
        cnf_frame.setLayout(cnf_grid)

        self.stp_save_cnf_but = PushButton('Save Config')
        self.stp_startup_profile_input = QtGui.QComboBox()

        self.stp_save_cnf_but.clicked.connect(self.actions.iconf_save)

        self.stp_startup_profile_input.currentIndexChanged.connect(self.actions.iconf_config_set_profile)

        cnf_grid.addWidget(self.stp_save_cnf_but, 0, 1)

        cnf_grid.addWidget(QtGui.QLabel('Operating mode'), 1, 0)
        cnf_grid.addWidget(self.stp_startup_profile_input, 1, 1)

        stp_tabs.addTab(pfl_frame, 'P&rofile')
        stp_tabs.addTab(cnf_frame, '&Config')

        grid.addWidget(stp_tabs, 0, 0)

        self.centralWidget().layout().addWidget(frame, 2, 0, 1, 2)

    def _status_section(self):
        sts_grid = QtGui.QGridLayout()
        sts_grid.setSpacing(10)

        sts_frame = QtGui.QGroupBox('Status')
        sts_frame.setLayout(sts_grid)

        self.sts_refresh_but = PushButton('Refresh')
        self.sts_refresh_interval_input = QtGui.QComboBox()
        self.sts_status_table = UpdatableTableWidget(0, 2, parent=sts_frame)
        self.sts_status_table.setHorizontalHeaderLabels(('Key', 'Value'))

        self.sts_refresh_interval_input.addItems(self.actions.REFRESH_VALUES)

        self.sts_refresh_but.clicked.connect(self.actions.request_status)
        self.sts_refresh_interval_input.currentIndexChanged.connect(self.actions.set_status_refresh_interval)
        self.actions.status.signal.connect(self.sts_status_table.update_content)

        sts_grid.addWidget(self.sts_refresh_but, 0, 0)

        sts_grid.addWidget(QtGui.QLabel('Refresh interval'), 0, 1)
        sts_grid.addWidget(self.sts_refresh_interval_input, 0, 2)
        sts_grid.addWidget(self.sts_status_table, 1, 0, 10, 3)

        self.centralWidget().layout().addWidget(sts_frame, 1, 2, 2, 1)

    def _profile_section(self):
        pass


if __name__ == '__main__':
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(base_path)
    fstyle = open(os.path.join(base_path, './style.qss'), 'r')
    with fstyle as f:
        style = f.readlines()
    root = QtGui.QApplication(sys.argv)
    root.setStyleSheet(' '.join(style))
    ertzagui = ErtzaGui()
    sys.exit(root.exec_())
