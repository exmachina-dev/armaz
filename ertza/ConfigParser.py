# -*- coding: utf-8 -*-

import logging
import os
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
        for cfg in args[0:-1]:
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
            variant = self.get('machine', 'variant', fallback=False)
            if not variant:
                logging.warn("Couldn't get variant from config")
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
