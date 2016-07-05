```
____ ____ ___ ___  ____ 
|___ |__/  |    /  |__| 
|___ |  \  |   /__ |  | 
 
```

# ertza

[![Travis CI](https://travis-ci.org/exmachina-dev/ertza.svg?branch=dev)](https://travis-ci.org/exmachina-dev/ertza)
[![Documentation Status](https://readthedocs.org/projects/ertza/badge/?version=latest)](http://ertza.readthedocs.io/en/latest/?badge=latest)

Continuous integration is currently not working.


This program provides all functionnalities for controlling Armaz motors. This software runs on a Beaglebone Black with a ArmazCape on top of it.
ArmazCape design files can be found in the [Bitbucket repository](https://bitbucket.org/exmachina-dev/eisla-electronics) or in the [Github repository](https://github.com/exmachina-dev/ertza).

The Beaglebone Black distro is build using [Yocto Project](www.yoctoproject.org).
A dedicated layer containing required recipes to build a full image for a Beaglebone Black is available at [Bitbucket](https://bitbucket.org/exmachina-dev/meta-exm-core) or at [Github](https://github.com/exmachina-dev/meta-exm-core).

Ertza is tested under Python v3.3 & v3.4

## Features

Ertza features:

- Cascading configuration files
- Modular driver interface
- Multiple control modes [torque, velocity, position and enhanced torque]
- Led driver
- Thermistor logger
- Fan PWM driver
- Configurable external switch
- Modular command structure allow to rapidly add a functionality in a protocol
- OSC Protocol
- Custom serial protocol for remote control
- Cortrol loop with slaves in different modes

## Things to do

Ertza will implement:

- DMX Protocol
- ArtNet protocol

## Dependencies
see requirements.txt
