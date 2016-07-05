Serial commands for profiles
============================

config.profile.load:PROFILE

Load existing profile found in _PROFILE_PATH (usually /etc/ertza/profiles)


config.profile.unload

Unload profile


config.profile.set:SECTION:OPTION:VALUE

Set value in profile (not in config)


config.profile.list_options

Return a list of assignable options:
ExmEislaLLSSSSSSSSSSSSconfig.profile.list_options.reply:SECTION:OPTION\r\n

The command always send a ok reply at the end of the dump:
ExmEislaLLSSSSSSSSSSSSconfig.profile.dump.ok\r\n


config.profile.dump

Dump profile content:
ExmEislaLLSSSSSSSSSSSSconfig.profile.dump.reply:SECTION:OPTION:VALUE\r\n

The command always send a ok reply at the end of the dump:
ExmEislaLLSSSSSSSSSSSSconfig.profile.dump.ok\r\n


config.profile.save:[PROFILE]

Save profile to a file in _PROFILE_PATH.
If PROFILE is empty, overwrites the loaded profile


config.save

Save config to custom.conf including the loaded profile name


config.get:SECTION:OPTION

Returns the value of SECTION:OPTION. This allow to verify the behaviour of the config.
This behaviour can be changed by variant config or profile.

Here is the config priority:

variant
profile
custom
machine
default

This ensure that none of the values defined in variant could be overwritten and
that the values defined in profile takes precedence over others (except variant).
This is to prevent end-user to modify limit values fixed for the machine
(i.e.: max_velocity of motor)

