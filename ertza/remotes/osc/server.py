# -*- coding: utf-8 -*-

import liblo as lo

from ...config import ConfigRequest
from ...errors import OSCServerError
from ..modbus import ModbusRequest


class OSCBaseServer(lo.Server):
    """
    Main OSC class herited from liblo.ServerThread

    Provides basic method to init and configure an OSC server working in a
    RemoteWorker instance.

    Require a pipe to ConfigWorker.
    """

    def __init__(self, config, logger=None, restart_event=None, **kwargs):
        """
        Init OSCServer with a ConfigParser instance and get server and client
        port.
        """

        self.running = True
        self.interval = 0

        self._config = config
        if 'modbus' in kwargs:
            self._modbus = kwargs['modbus']
            self.mdb_request = ModbusRequest(self._modbus)
        else:
            self._modbus = None

        if logger:
            self.lg = logger
        else:
            import logging
            self.lg = logging.getLogger()

        self.osc_event = restart_event

        self.config_request = ConfigRequest(self._config)
        if 'no_config' in kwargs and kwargs['no_config'] == True:
            self.ready = False
        else:
            self.server_port = int(self.config_request.get(
                'osc', 'server_port', 7900))
            self.client_port = int(self.config_request.get(
                'osc', 'client_port', 7901))
            self.broadcast_address = self.config_request.get(
                'osc', 'broadcast', '192.168.1.255')

            self.create_server()

    def create_server(self):
        try:
            super(OSCBaseServer, self).__init__(self.server_port, lo.UDP)
            self.ready = True
        except lo.ServerError as e:
            final_error = OSCServerError(e)
            self.lg.error(final_error)
            self.ready = False
            raise final_error

    def run(self, timeout=None):
        if self.running:
            self.recv(timeout)

    def start(self, blocking=True):
        """
        Start the OSC Server loop.
        """

        self.running = True

        if self.ready:
            if blocking:
                self.lg.debug("%s started on %s",
                        type(self).__name__, self.server_port)
                while self.running:
                    self.run(self.interval)
            else:
                self.lg.debug("%s initialized on %s",
                        type(self).__name__, self.server_port)
                self.run(0)

    def announce(self):
        address = lo.Address(self.broadcast_address, self.client_port)
        msg = lo.Message('/status/online', self.server_port)
        return self.send(address, msg)

    def stop(self):
        self.running = False

    def restart(self):
        """
        Restart the OSC Server thread.

        Actually set the restart event. Restarting is handle by the
        OSCWorker.
        """

        try:
            self.osc_event.set()
        except AttributeError:
            self.lg.warn('No restart event was supplied at init.')

    def send(self, dst, msg):
        return super(OSCBaseServer, self).send(
                lo.Address(dst.get_hostname(), self.client_port), msg)

    def reply(self, default_path, sender, *args, **kwargs):
        if kwargs and 'merge' in kwargs.keys():
            kwargs['merge'] = True
        else:
            kwargs['merge'] = False

        try:
            if type(args[0]) == str and args[0][0] == '/':
                args = list(args)
                _msg = lo.Message(args.pop(0), *args)
            elif len(args) >= 2 and kwargs['merge']:
                args = list(args)
                path = args.pop(0)
                _msg = lo.Message(default_path+'/'+path, *args)
            else:
                _msg = lo.Message(default_path, *args)
        except (TypeError, KeyError):
            _msg = lo.Message(default_path, *args)
        self.send(sender, _msg)
        return _msg
