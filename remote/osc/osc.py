#!/usr/bin python3
# -*- coding: utf-8 -*-

import configparser
import liblo as lo

class OSCServer(lo.ServerThread):
    """
    Main OSC class herited from liblo.ServerThread

    Provides basic method to init and configure an OSC server working in a
    RemoteWorker instance.

    Require a ConfigParser object (or a proxy) as init argument.
    """

    def __init__(self, config):
        """
        Init OSCServer with a ConfigParser() instance and get server and client
        port.
        """

        self.config = config
        self.server_port = self.config.get('osc', 'server_port')
        self.client_port = self.config.get('osc', 'client_port')
        super(OSCServer, self).__init__(self.server_port, lo.UDP)
        self.ready = True

    def start(self):
        """
        Start the OSC Server thread.
        """

        super(OSCServer, self).start()

    def send(self, dst, msg):
        super(OSCServer, self).send(lo.Address(dst.get_hostname(), self.client_port), msg)

class OSCCommands(OSCServer):
    """
    OSCCommands contains all commands available thru OSCServer.
    """
    _commands_store = {

    }

    def setup_reply(self, sender, *args):
        _msg = lo.Message('/setup/return', *args)
        self.send(sender, _msg)

    @lo.make_method('/setup/set', 'ssi')
    @lo.make_method('/setup/set', 'ssh')
    @lo.make_method('/setup/set', 'ssf')
    @lo.make_method('/setup/set', 'ssd')
    @lo.make_method('/setup/set', 'ssc')
    @lo.make_method('/setup/set', 'sss')
    @lo.make_method('/setup/set', 'ssS')
    @lo.make_method('/setup/set', 'ssm')
    @lo.make_method('/setup/set', 'ssT')
    @lo.make_method('/setup/set', 'ssF')
    @lo.make_method('/setup/set', 'ssN')
    @lo.make_method('/setup/set', 'ssI')
    @lo.make_method('/setup/set', 'ssb')
    def setup_set_callback(self, path, args, types, sender):
        setup_sec, setup_opt, args, = args
        print(self.config.sections())

        try:
            self.config.set(setup_sec, setup_opt, str(args))
            self.setup_reply(sender, setup_sec, setup_opt, True)
        except configparser.NoOptionError as err:
            self.setup_reply(sender, setup_sec, str(err))
        except configparser.NoSectionError as err:
            self.setup_reply(sender, str(err))
        except:
            self.setup_reply(sender, str(ValueError))

        print(path, setup_sec, setup_opt, args, types, sender)
        return 0

    @lo.make_method('/setup/get', 'ss')
    def setup_get_callback(self, path, args, types, sender):
        if len(args) != 2:
            return 1
        setup_section, setup_var = args
        try:
            args.append(self.config.get(setup_section, setup_var))
            self.setup_reply(sender, *args)
        except configparser.NoOptionError as err:
            print(sender, err)
            self.setup_reply(sender, setup_section, str(err))
        return 0

    #def setConfig(self, c):
    #    for k, l in c:
    #        if k in ('feedback',):
    #            if k == 'feedback':
    #                self.feedback = bool(*l)

    #def getConfig(self):
    #    rtn = dict()
    #    rtn.update({'feedback', int(self.feedback), })

    #    return rtn

    #def heartbeat(self, destination, ok=True, src=None):
    #    if ok:
    #        state = '/ok'
    #    else:
    #        state = '/nok'
    #    if not src:
    #        src = 'mother'
    #    self.send(destination, '/heartbeat' + state + '/' + src)
