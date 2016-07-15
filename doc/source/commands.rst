Commands
========

Commands defines a way for remotes to interact with ertza. They also defines the public API for the slave machimism.

Commands are protocol dependant. This allow to customize behaviour and arguments required on a per-protocol basis.

The two main protocols currently supported are OSC_ and a custom :doc:`serial protocol<protocol-serial>`.

OSC commands
------------

.. automodule:: ertza.commands.osc
   :members:
   :show-inheritance:

Serial commands
---------------

.. automodule:: ertza.commands.serial
   :members:
   :show-inheritance:

.. _OSC: http://opensoundcontrol.org
.. _serial protocol: protocol-serial
