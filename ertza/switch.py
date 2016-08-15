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

from threading import Thread, Event
import logging

logging = logging.getLogger('ertza.switch')


class Switch(object):

    callback = None                 # Override this to get events

    def __new__(cls, inputdev):
        cls._inputdev = inputdev
        cls._thread = Thread(target=cls._wait_for_events)
        cls._thread.daemon = True
        cls._running_event = Event()
        cls._keycodes = {}

        return super().__new__()

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
    def start(cls):
        if len(cls._keycodes):
            raise ValueError('No keycodes assigned to {0.__name__}, '
                             'cannot start.'.format(cls))

        if cls.inputdev is None:
            raise ValueError('Inputdev cannot be None.')

        try:
            cls._thread.start()
        except RuntimeError:
            logging.info('{0.__name__} already started.'.format(cls))

    @classmethod
    def get_key_config(cls, keycode):
        config = cls._keycodes[keycode].copy()
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

    def __repr__(self):
        i = {
            'name': self.name,
            'keycode': self.key_code,
            'dir': self.direction,
            'hit': self.hit,
        }

        return 'Switch {name} at {keycode} (dir {dir} hit {hit})'.format(**i)

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
