# -*- coding: utf-8 -*-

from ertza.commands.SerialCommand import SerialCommand


class ConfigLoadProfile(SerialCommand):
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


class ConfigProfileDump(SerialCommand):
    def execute(self, c):
        if not self.check_args(c, 'le', 1):
            return

        try:
            if c.args:
                profile = c.args
            else:
                profile = None

            dump = self.machine.config.profile_dump(profile)
            for sec, opts in enumerate(dump):
                for opt, val in enumerate(opts):
                    self.reply(c, sec, opt, val)

            self.ok(c, 'done')
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return 'config.profile.dump'


class ConfigProfileSave(SerialCommand):
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
