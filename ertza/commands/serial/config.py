# -*- coding: utf-8 -*-

from ertza.commands import SerialCommand


class ConfigLoadProfile(SerialCommand):
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
        return 'config.profile.load'


class ConfigUnloadProfile(SerialCommand):
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
        return 'config.profile.unload'


class ConfigProfileSet(SerialCommand):
    """
    Set value in profile (not in config)
    """

    def execute(self, c):
        if not self.check_args(c, 'ne', 3):
            return

        try:
            sec, opt, value = c.args
            self.machine.config.profile_set(sec, opt, value)
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return 'config.profile.set'


class ConfigProfileListOptions(SerialCommand):
    """
    Return a list of assignable options:
    ExmEislaLLSSSSSSSSSSSSconfig.profile.list_options.reply:SECTION:OPTION\r\n

    The command always send a ok reply at the end of the dump:
    ExmEislaLLSSSSSSSSSSSSconfig.profile.dump.ok\r\n
    """
    def execute(self, c):

        try:
            opts = self.machine.config.profile_list_options()
            for sec, opts in enumerate(list):
                for opt, vtype in enumerate(opts):
                    self.reply(c, sec, opt)

            self.ok(c, 'done')
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return 'config.profile.list_options'

    @property
    def help_text(self):
        return 'Return a list of options that can be saved into a profile'


class ConfigProfileDump(SerialCommand):
    """
    Dump profile content:
    ExmEislaLLSSSSSSSSSSSSconfig.profile.dump.reply:SECTION:OPTION:VALUE\r\n

    The command always send a ok reply at the end of the dump:
    ExmEislaLLSSSSSSSSSSSSconfig.profile.dump.ok\r\n
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
        return 'config.profile.dump'


class ConfigProfileSave(SerialCommand):
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
        return 'config.profile.save'


class ConfigSave(SerialCommand):
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
        return 'config.save'


class ConfigGet(SerialCommand):
    """
    config.get:SECTION:OPTION

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
        return 'config.get'
