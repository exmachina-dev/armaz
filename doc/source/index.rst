.. Ertza documentation master file, created by
   sphinx-quickstart on Tue Jul  5 12:02:46 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Ertza's documentation
================================

Ertza is a python program providing a simple, yet powerful, gateway between motor drive and protocols such as OSC or DMX.

It's designed to work on a BeagleBone Black with an ArmazCape on top.
For ArmazCape schematics and PCB design, please refer to `eisla-electronics repository`_.

Ertza is usually embedded into Elias distro which is build using `Yocto Project`_.
Elias main layer can be found at `meta-exm-core repository`_

Ertza features:

* Communication with motor drive (via an extensible driver nodule interface)
  Currently only ModBus TCP is supported. A debug fake driver is also provided.
* Key events based on interrupts to expose basic actions or limit switches
* Remote control via multiple protocols.
  Currently OSC and a serial protocol are implemented
* Cascading configuration scheme
* Configuration managed through profiles that allow quick reconfiguration
* Temperature watcher
* Fan regulator
* Configurable LED system

Contents:

.. toctree::
   :maxdepth: 2

   config
   commands
   profiles
   protocol-serial
   tools


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _eisla-electronics repository: https://github.com/exmachina-dev/eisla-electronics
.. _Yocto Project: https://www.yoctoproject.org
.. _meta-exm-core repository: https://github.com/exmachina-dev/meta-exm-core
