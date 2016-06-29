# -*- coding: utf-8 -*-


class ModbusDriverFrontend(object):

    def load_config(self, config):
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

        self.control_mode = self._safe_config_get("control_mode", int, 2)

        self.entq = {}
        self.entq['kp'] = self._safe_config_get("entq_kp", float, 1.15)
        self.entq['kp_vel'] = self._safe_config_get("entq_kp_vel", float, 1)
        self.entq['ki'] = self._safe_config_get("entq_ki", float, 0.1)
        self.entq['kd'] = self._safe_config_get("entq_kd", float, 5)

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
        self['command:control_mode'] = self.control_mode
        self['acceleration'] = self.acceleration
        self['deceleration'] = self.deceleration
        self['torque_rise_time'] = self.torque_rise_time
        self['torque_fall_time'] = self.torque_fall_time
        for k, v in self.entq.items():
            self['entq_{}'.format(k)] = v

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

            value = value * -1 if self.invert else value
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
            value = value * -1 if self.invert else value
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
            value = value * -1 if self.invert else value
        elif key in ('torque'):
            value /= self.gearbox_ratio
            value = value * -1 if self.invert else value
        elif key in ('current_ratio'):
            value = value * -1 if self.invert else value

        return value

    def _input_value(self, key, value):
        return self._input_value_coefficient(key, value)

    def _safe_config_get(self, key, vtype=None, fallback=None):
        try:
            if vtype:
                if vtype == bool:
                    return True if self.frontend_config[key] in ('True', 'true', 'y', '1') else False
                return vtype(self.frontend_config[key])
            else:
                return self.frontend_config[key]
        except KeyError:
            return fallback
