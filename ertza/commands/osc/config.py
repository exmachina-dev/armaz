# -*- coding: utf-8 -*-

from ertza.commands import UnbufferedCommand
from ertza.commands import OscCommand


class ConfigLoadProfile(UnbufferedCommand, OscCommand):
    """
    Load existing profile found in _PROFILE_PATH (usually /etc/ertza/profiles)
    """

    def execute(self, c):
        if self.check_args(c, 'ne', 1):
            self.error(c, 'Invalid number of arguments for %s' % self.alias)

        try:
            profile = c.args
            self.machine.config.load_profile(profile)
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/load'

    @property
    def help_text(self):
        return 'Load the specified PROFILE'

    @property
    def args(self):
        return 'PROFILE'


class ConfigUnloadProfile(UnbufferedCommand, OscCommand):
    """
    Unload loaded profile (if any)
    """

    def execute(self, c):
        try:
            self.machine.config.unload_profile()
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/unload'

    @property
    def help_text(self):
        return 'Unload the loaded profile (if any)'


class ConfigProfileSet(UnbufferedCommand, OscCommand):
    """
    Set value in profile (not in config)
    """

    def execute(self, c):
        if not self.check_args(c, 'ne', 2):
            return

        try:
            dest, value = c.args
            sec, opt = dest.split(':')
            self.machine.config.profile_set(sec, opt, value)
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/set'

    @property
    def help_text(self):
        return 'Set the VALUE in SECTION:OPTION'

    @property
    def args(self):
        return 'SECTION:OPTION VALUE'


class ConfigProfileListOptions(UnbufferedCommand, OscCommand):
    """
    Return a list of assignable options:
    /config/profile/list_options/reply SECTION:OPTION

    The command always send a ok reply at the end of the dump:
    /config/profile/list_options/ok done
    """
    def execute(self, c):

        try:
            list_opts = self.machine.config.get_profile_options()
            for sec, opts in list_opts.items():
                for opt, vtype in opts.items():
                    self.reply(c, '{}:{}'.format(sec, opt))

            self.ok(c, 'done')
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/list_options'

    @property
    def help_text(self):
        return 'Return a list of options that can be saved into a profile'


class ConfigProfileDump(UnbufferedCommand, OscCommand):
    """
    Dump profile content:
    /config/profile/dump/reply SECTION:OPTION VALUE\r\n

    The command always send a ok reply at the end of the dump:
    /config/profile/dump/ok done\r\n
    """
    def execute(self, c):
        if not self.check_args(c, 'le', 1):
            return

        try:
            if c.args:
                profile = c.args
            else:
                profile = None

            dump = self.machine.config.profile_dump(profile)
            for options, val in dump.items():
                sec, opt = options
                self.reply(c, sec, opt, val)

            self.ok(c, 'done')
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/dump'

    @property
    def help_text(self):
        return 'Dump actual profile values '


class ConfigProfileSave(UnbufferedCommand, OscCommand):
    """
    Save profile to a file in _PROFILE_PATH.
    If PROFILE is empty, overwrites the loaded profile
    """

    def execute(self, c):
        if not self.check_args(c, 'le', 1):
            return

        try:
            if c.args:
                profile = c.args
            else:
                profile = None

            self.machine.config.profile_save(profile)
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/save'

    @property
    def help_text(self):
        return 'Save the specified PROFILE (or the loaded one if unspecified)'

    @property
    def args(self):
        return '[PROFILE]'


class ConfigSave(UnbufferedCommand, OscCommand):
    """
    Save config to custom.conf including the loaded profile name
    """

    def execute(self, c):
        try:
            self.machine.config.save()
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/save'

    @property
    def help_text(self):
        return 'Save the current config into the custom config file'


class ConfigGet(UnbufferedCommand, OscCommand):
    """
    Returns the value of SECTION:OPTION. This allow to verify the behaviour of the config.
    This behaviour can be changed by variant config or profile.
    """

    def execute(self, c):
        if len(c.args) != 1:
            self.error(c, 'Invalid number of arguments for %s' % self.alias)
            return

        try:
            k, = c.args
            nk = k.decode().replace('.', ':')
            v = self.machine[nk]
            self.ok(c, k, v)
        except Exception as e:
            self.error(c, k, str(e))

    @property
    def alias(self):
        return '/config/get'

    @property
    def help_text(self):
        return 'Returns the value of SECTION:OPTION'

    @property
    def args(self):
        return 'SECTION:OPTION'
