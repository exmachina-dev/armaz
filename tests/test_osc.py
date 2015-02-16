# -*- coding: utf-8 -*-

from ertza.remotes.osc import OSCServer
from ertza.config import ConfigRequest
from ertza.utils import FakeConfig

import liblo

class Test_OSCServer(object):
    def setup_class(self):
        class ModifiedOSCServer(OSCServer):
            def setup_reply(self, sender, *args):
                self.message = \
                        super(ModifiedOSCServer, self).setup_reply(
                                sender, *args)


        self.osc = ModifiedOSCServer(FakeConfig(), None, None)
        self.crq = ConfigRequest(FakeConfig())

        self.osc.start(blocking=False)

        self.target = liblo.Address(int(self.crq.get('osc', 'server_port')))
        self.to = int(self.crq.get('osc', 'client_port'))

        self.osc2 = liblo.Server(self.to)

        def fallback(path, args, types, src):
            print("got message '%s' from '%s'" % (path, src.url))
            self.output = list(args)
            self.output.insert(0, path)

        self.osc2.add_method(None, None, fallback)

    def test_set(self):
        liblo.send(self.target, "/setup/set", 'osc', 'client_port', 12)
        self.osc.run()
        self.osc2.recv(100)
        assert type(self.osc.message) == liblo.Message
        assert self.output == ['/setup/set', 'osc', 'client_port', '12']

        liblo.send(self.target, "/setup/set",'fake_section', 'server_port')
        self.osc.run()
        self.osc2.recv(100)
        assert type(self.osc.message) == liblo.Message
        assert self.output == ['/status/wrong_osc_command', '/setup/set',
                'ss', 'fake_section', 'server_port']

    def test_get(self):
        liblo.send(self.target, "/setup/get", 'osc', 'server_port')
        self.osc.run()
        self.osc2.recv(100)
        assert type(self.osc.message) == liblo.Message
        assert self.output == ['/setup/get', 'osc', 'server_port',
                self.crq.get('osc', 'server_port')]

        liblo.send(self.target, "/setup/get", 'fake_section', 'server_port')
        self.osc.run()
        self.osc2.recv(100)
        assert type(self.osc.message) == liblo.Message
        assert self.output == ['/setup/return', 'fake_section',
                "No section: 'fake_section'"]
