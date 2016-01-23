# -*- coding: utf-8 -*-

import logging
import os
import struct
import configparser

_VARIANT_PATH = "/etc/ertza/variants"


class ConfigParser(configparser.ConfigParser):
    """
    ConfigParser provides config interface. Its handle cascading config files.
    """

    def __init__(self, *args):
        self.variant_loaded = False
        self.variant = None

        super(ConfigParser, self).__init__(
            interpolation=configparser.ExtendedInterpolation())

        self.config_files = []
        for cfg in args:
            self.config_files.append(os.path.realpath(cfg))

        for cfg in self.config_files:
            if os.path.isfile(cfg):
                logging.info("Found " + cfg)
                self.read_file(open(cfg))
            else:
                logging.warn("Config file %s not found" % cfg)

    def load_variant(self, variant=None):
        """
        Load variant config file.

        If variant is not specified, load variant value defined in config file.
        """

        if self.variant_loaded:
            logging.warn("Variant already loaded: %s" % self.variant)
            return False
        if not variant:
            cape_infos = self.find_cape()
            if cape_infos:
                try:
                    variant = cape_infos['variant'].lower()
                except Exception as e:
                    logging.warn('Got exception while decoding eeprom: {!s}'.format(e))
            if not variant:
                logging.warn("Couldn't get variant from eeprom")
                variant = self.get('machine', 'variant', fallback=False)

            if not variant:
                logging.warn("Couldn't get variant from eeprom or config")
                return False

        variant_cfg = os.path.join(_VARIANT_PATH, variant + ".conf")
        if os.path.isfile(variant_cfg):
            logging.info("Loading variant config file: %s" % variant)
            variant_cfg = os.path.realpath(variant_cfg)
            self.config_files.append(variant_cfg)
            self.read_file(open(variant_cfg))
            self.variant_loaded = True
            self.variant = variant
        else:
            logging.warn("Couldn't find variant config file " + variant_cfg)

    def save(self):
        """
        Save only modified values in custom config.
        This is like (current_config - default_config) - variant_config
        """

        stop_index = -2 if self.variant_loaded else -1
        def_configfiles = self.config_files[0:stop_index]
        custom_configfile = self.config_files[stop_index]

        def_config = ConfigParser(*def_configfiles)
        save_config = ConfigParser()
        for sec in self.sections():
            if def_config.has_section(sec):
                save_config.add_section(sec)
                for opt in self[sec]:
                    if opt in def_config[sec]:
                        if self[sec][opt] != def_config[sec][opt]:
                            save_config[sec][opt] = self[sec][opt]

                if not len(save_config[sec]):
                    save_config.remove_section(sec)

        if self.variant_loaded:
            var_config = ConfigParser(self.config_files[-1])
            for sec in var_config.sections():
                if save_config.has_section(sec):
                    for opt in var_config[sec]:
                        save_config.remove_option(sec, opt)

        with open(custom_configfile, 'w') as cf:
            save_config.write(cf)

    def find_cape(self, partnumber='ARMAZCAPE'):
        capes = self.get_cape_infos()
        for c in capes:
            if not c:
                continue
            if c['partnumber'] == partnumber:
                return c

    def get_cape_infos(self):
        capes = list()
        for addr in range(4, 7):
            path = '/sys/bus/i2c/devices/2-005%d/eeprom' % addr
            if os.path.isfile(path):
                capes.append(self.get_eeprom_infos(path))
            else:
                continue

        return capes

    def get_eeprom_infos(self, eeprom):
        try:
            with open(eeprom, "rb") as f:
                data = f.read(260)
                try:
                    infos = {
                        'eeprom_header': data[0:4],
                        'eeprom_rev': data[4:6].decode(),
                        'name': data[6:38].strip().decode(),
                        'revision': data[38:42].decode(),
                        'manufacturer': data[42:58].strip().decode(),
                        'partnumber': data[58:74].strip().decode(),
                        'nb_pins_used': struct.unpack('>h', data[74:76])[0],
                        'serialnumber': data[76:88].decode(),
                        'variant': data[244:260].strip().decode(),
                    }
                    return infos
                except UnicodeDecodeError as e:
                    logging.error('Error while decoding eeprom: {!s}'.format(e))
                    return False
        except IOError as e:
            logging.error('Error while reading eeprom: {!s}'.format(e))
            return False
