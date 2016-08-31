#!/usr/bin/env python
"""
A class that listens for a button press
and sends an event if that happens.

This code is extracted from Redeem. Original source code can be found at:
    https://bitbucket.org/intelligentagent/redeem/src

Original author: Elias Bakken
Email: elias(dot)bakken(at)gmail(dot)com
Released under license: GNU GPL v3: http://www.gnu.org/copyleft/gpl.html

Code modified by Benoit Rapidel:
    Ported to python 3
    Better handling of direction and hit
    Removed PRU section
    Use a single thread
"""

import os
import logging
import struct
from threading import Thread, Event
from types import SimpleNamespace
from collections import namedtuple

from .exceptions import AbstractErtzaException

logging = logging.getLogger('ertza.switch')


class SwitchException(AbstractErtzaException):
    pass


class InputEvent(object):
    _EventStruct = namedtuple('Event', ('timecode', 'evtype', 'keycode', 'value', 'unk'))

    def __init__(self, ev):
        try:
            self.ev_data = self._EventStruct._make(struct.unpack('<dHHHH', ev))
        except struct.error:
            raise ValueError('Misformated event bytes')

    def __getattr__(self, attr):
        return getattr(self.ev_data, attr)

    def __str__(self):
        return 'T: {0.evtype} K: {0.keycode} V: {0.value}'.format(self)

    def __repr__(self):
        return '{0.__class__.__name__}({0!s})'.format(self)


EventTypes = SimpleNamespace(SYN=0, KEY=1, REL=2, ABS=3, MSC=4, SW=5, REP=6)


class Switch(object):

    callback = None                 # Override this to get events
    _thread = None
    _inputdev = None
    _keycodes = {}

    def __init__(self, keycode, name, **kwargs):
        keycode_conf = {
            'name': name,
            'invert': kwargs.pop('invert', False),
            'function': kwargs.pop('function', False),
            'hit': False,
            'direction': None,
        }
        self._keycodes[keycode] = keycode_conf
        self.keycode = keycode

    @classmethod
    def set_inputdev(cls, inputdev):
        if os.path.exists(inputdev):
            cls._inputdev = inputdev
        else:
            raise FileNotFoundError('{} not found.'.format(inputdev))

    @classmethod
    def start(cls):
        if cls._inputdev is None:
            raise ValueError('Inputdev cannot be None.')

        try:
            if cls._thread is None:
                cls._thread = Thread(target=cls._wait_for_events)
                cls._thread.daemon = True
                cls._running_event = Event()

            cls._thread.start()
        except RuntimeError:
            logging.info('{0.__name__} already started.'.format(cls))
            raise

    @classmethod
    def get_key_config(cls, keycode):
        config = dict(cls._keycodes[keycode])
        return config

    @classmethod
    def get_key_state(cls, keycode):
        state = cls.get_key_config(keycode)
        state.update({'keycode': keycode})
        return state

    @property
    def state(self):
        return self.get_key_state(self.keycode)

    @property
    def key_config(self):
        return self.get_key_config(self.keycode)

    @classmethod
    def _wait_for_events(cls):
        try:
            with open(cls._inputdev, 'rb') as evt_file:
                while not cls._running_event.is_set():
                    evt = cls._get_event(evt_file)

                    if evt is None:
                        continue

                    cls._process_event(evt)
        except OSError as e:
            logging.error('Unable to access to inputdev file: {!s}'.format(e))
            raise SwitchException(str(e))

    @classmethod
    def _get_event(cls, fd):
        ev_data = fd.read(16)

        if len(ev_data) == 16:
            return InputEvent(ev_data)

    @classmethod
    def _process_event(cls, evt):
        if evt.evtype != EventTypes.KEY:
            logging.debug('Ignored {!s}'.format(evt))
            return

        logging.debug('Got {!s}'.format(evt))

        if evt.keycode in cls._keycodes.keys():
            cnf = cls.get_key_config(evt.keycode)
            k_dir = True if evt.value else False
            k_hit = True if (cnf['invert'] and cnf['direction']) or \
                (not cnf['invert'] and not cnf['direction']) else False

            cls._keycodes[evt.keycode]['direction'] = k_dir
            cls._keycodes[evt.keycode]['hit'] = k_hit

            if cls.callback is not None:
                try:
                    cls.callback(cls.get_key_state(evt.keycode))
                except Exception as e:
                    logging.warn('Exception in {!s}: {!s}'.format(cls, e))
        else:
            logging.debug('Got unrecognized keycode: {}'.format(evt.keycode))

    def __repr__(self):
        return 'Switch {name} at {keycode} ' \
               '(dir {direction} hit {hit})'.format(**self.state)

if __name__ == '__main__':
    import signal

    def cb(event):
        print(event)

    Switch.callback = cb
    keycodes = (112, 113, 114, 115, 116)
    for k in keycodes:
        n = 'SW%i' % (k - 112)
        s = Switch(k, n)

    signal.pause()
