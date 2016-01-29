# -*- coding: utf-8 -*-

import logging


class ModbusDriverFrontend(object):

    def load_frontend_config(self, config):
        self.frontend_config = config

        self.gearbox_ratio = (float(config["gearbox_input_coefficient"]) /
                              float(config["gearbox_output_coefficient"]))

        # Limits
        self.max_velocity = float(config["max_velocity"])
        self.max_acceleration = float(config["max_acceleration"])
        self.max_deceleration = float(config["max_deceleration"])

        self.min_torque_rise_time = float(config["min_torque_rise_time"])
        self.min_torque_fall_time = float(config["min_torque_fall_time"])

        # Actual values
        self.acceleration = float(config["acceleration"])
        self.deceleration = float(config["deceleration"])

        self.torque_rise_time = float(config["torque_rise_time"])
        self.torque_fall_time = float(config["torque_fall_time"])

        # Application parameters
        self.application_coeff = float(config.get('application_coefficient', 1))
        self.invert = True if config.get('invert', '') == 'True' else False
        self.acceleration_time_mode = True if config.get('acceleration_time_mode', '') == 'True' else False

        self.custom_max_velocity = float(config["custom_max_velocity"]) or None
        self.custom_max_acceleration = float(config["custom_max_acceleration"]) or None
        self.custom_max_deceleration = float(config["custom_max_deceleration"]) or None

        self.custom_max_position = float(config["custom_max_position"]) or None
        self.custom_min_position = float(config["custom_min_position"]) or None

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
            value = value * -1 if not self.invert else value

            if self.custom_max_velocity is not None and key == 'velocity_ref':
                value = value if value < self.custom_max_velocity else self.custom_max_velocity
                value = value if value > -self.custom_max_velocity else -self.custom_max_velocity
            elif self.custom_max_position is not None and key == 'position_ref':
                value = value if value < self.custom_max_position else self.custom_max_position
            elif self.custom_min_position is not None and key == 'position_ref':
                value = value if value > self.custom_min_position else self.custom_min_position
                if value == self.custom_min_position:
                    logging.warn('Min position limit reached, clamping value')

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

        return value

    def _output_value(self, key, value):
        return self._output_value_limit(key, self._output_value_coefficient(key, value))

    def _input_value_coefficient(self, key, value):
        if key in ('velocity_ref', 'position_ref',):
            value /= self.application_coeff
            value *= self.gearbox_ratio
        if key in ('acceleration', 'deceleration',):
            value *= self.gearbox_ratio
            value /= self.application_coeff
            if self.acceleration_time_mode:
                value = (self.max_velocity / self.gearbox_ratio * self.application_coeff) / value

        return value

    def _input_value(self, key, value):
        return self._input_value_coefficient(key, value)
