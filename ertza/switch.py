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
from threading import Thread, Event
import logging

from .exceptions import AbstractErtzaException

logging = logging.getLogger('ertza.switch')


class SwitchException(AbstractErtzaException):
    pass


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
            'hit': kwargs.pop('hit', False),
            'direction': kwargs.pop('direction', None),
        }
        self._keycodes[keycode] = keycode_conf
        self.keycode = keycode

    @classmethod
    def set_inputdev(cls, inputdev):
        if os.path.isfile(inputdev):
            cls._inputdev = inputdev
        else:
            raise FileNotFoundError('{} not found.'.format(inputdev))

    @classmethod
    def start(cls):
        if cls._inputdev is None:
            raise ValueError('Inputdev cannot be None.')

        try:
            if cls._thread is None:
                cls._thread = Thread(target=Switch._wait_for_events)
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
        state['keycode'] = keycode
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
                    evt = evt_file.read(16)     # Read the event
                    evt_file.read(16)           # Discard the debounce event

                    if evt == b'':
                        continue

                    keycode = evt[10]

                    if keycode in cls._keycodes.keys():
                        cnf = cls.get_key_config(keycode)
                        k_dir = True if evt[12] else False
                        k_hit = True if (cnf['invert'] and cnf['direction']) or \
                            (not cnf['invert'] and not cnf['direction']) else False

                        cls._keycodes[keycode]['direction'] = k_dir
                        cls._keycodes[keycode]['hit'] = k_hit

                        if Switch.callback is not None:
                            try:
                                Switch.callback(cls.get_key_state(keycode))
                            except Exception as e:
                                logging.warn('Exception in {!s}: {!s}'.format(cls, e))
                    else:
                        logging.debug('Got unrecognized keycode: {}'.format(keycode))
        except OSError as e:
            logging.error('Unable to acces to inputdev file: {!s}'.format(e))
            raise SwitchException(str(e))

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
