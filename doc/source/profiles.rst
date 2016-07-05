Profiles
========

Profile system provides a quick way to store, load and modify parameters in ertza.
It also ensure that critical parameters (like max_velocity) cannot be overwritten by user input

Listed commands are given using OSC protocol but are also available through `serial protocol`_ 

List profiles
-------------

.. autoclass:: ertza.commands.osc.ConfigProfileList
   :noindex:


Load profile
------------

.. autoclass:: ertza.commands.osc.ConfigProfileLoad
   :noindex:

Unload profile
--------------

.. autoclass:: ertza.commands.osc.ConfigProfileUnload
   :noindex:

Dump profile
------------

.. autoclass:: ertza.commands.osc.ConfigProfileDump
   :noindex:

List profile options
--------------------

.. autoclass:: ertza.commands.osc.ConfigProfileListOptions
   :noindex:

Set profile option
------------------

.. autoclass:: ertza.commands.osc.ConfigProfileSet
   :noindex:

Save profile
------------

.. autoclass:: ertza.commands.osc.ConfigProfileSave
   :noindex:

.. _serial protocol: protocol-serial
