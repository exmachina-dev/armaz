Configuration files
===================

Configuration system in ertza is based on a cascading system
By default configuration files are placed under /etc/ertza.

Configuration types
-------------------

Three types of configurations files exists within ertza:

* Base configuration file: specify base parameters for ertza
  Most parameters are specified at startup and are never changed

* Variant configuration file: specify variant specific parametrs
  Usually stored under /etc/ertza/variants
  This allow to handle multiple variants of Armaz with different speeds, torque, etc...

* Profile configuration file: specify application related parameters
  Usually stored under /etc/ertza/profiles
  This give a easy way to configure Ertza for a specific application (see `profile section`_)


Base configuration files
------------------------

There is three base configuration files:

1) default.conf stores default values for ertza

2) machine.conf stores machine specific values (mostly drive related values)

3) custom.conf stores modified values like the loaded profile

They are loaded in sequence. This ensure that the default value for a parameter stored in default.conf will be overwritten if defined in machine.conf or custom.conf

Configuration predecence
------------------------

To guaranty the precedence between each configuration type, Ertza maintain a map where each configuration file has it's own priority:

1) variant.conf
2) profile.conf
3) custom.conf
4) machine.conf
5) default.conf

This ensure that none of the values defined in variant.conf could be overwritten and
that the values defined in profile.conf takes precedence over others (except variant.conf).

This is to prevent end-user to modify limit values fixed for the machine
(i.e.: max_velocity of motor)


.. _profile section: profiles.html
