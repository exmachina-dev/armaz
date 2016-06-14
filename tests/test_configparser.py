# -*- coding: utf-8 -*-

import pytest

from ertza.configparser import ConfigParser, NoSectionError, NoOptionError, ParsingError


class Test_ConfigParser(object):
    def setup_class(self):
        self.cf = ConfigParser('./tests/test.conf')

    def test_load_variant(self):
        self.cf.load_variant('variant', variant_path='./tests')

    def test_load_profile(self):
        self.cf.load_profile('profile', profile_path='./tests')

    def test_get(self):
        assert self.cf['machine']['profile'] == 'profile'

        with pytest.raises(NoSectionError):
            self.cf.get('fake_section', 'fake_option')

        with pytest.raises(NoOptionError):
            self.cf.get('machine', 'fake_option')


        assert self.cf.get('fake_section', 'fake_option', fallback=1234) == 1234

    def test_set(self):
        with pytest.raises(KeyError):
            self.cf['fake_section']['fake_option'] = 0

        with pytest.raises(TypeError):
            self.cf['machine']['force_serialnumber'] = 0

        self.cf['machine']['force_serialnumber'] = '1111'
        assert self.cf['machine']['force_serialnumber'] == '1111'
