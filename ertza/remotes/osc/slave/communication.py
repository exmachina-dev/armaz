# -*- coding: utf-8 -*-

from ....base import BaseRequest, BaseResponse
from ....utils import timeout
from ....errors import TimeoutError

class SlaveRequest(BaseRequest):
    def register(self, *args):
        return self._build_rq('register_slave', *args)

    def get_mode(self, *args):
        return self._build_rq('get_mode', *args)

    def get_master(self, *args):
        return self._build_rq('get_master', *args)

    def get_slaves(self, *args):
        return self._build_rq('get_slaves', *args)

    def set_master(self, *args):
        return self._build_rq('set_master', *args)

    def dump(self, *args):
        return self._build_rq('dmp', *args)


class SlaveResponse(BaseResponse):
    def __init__(self, target, request, end=None, *args):
        super(SlaveResponse, self).__init__(target, *args)
        self.request = request
        self._end = end

    def get_from_device(self, *args):
        if not self._end:
            raise ValueError("Slave server isn't defined.")

        if self.request.method == self._methods['get_mode']:
            self.method = self._methods['get_mode']
            self.value = self._end.mode
        elif self.request.method == self._methods['get_master']:
            self.method = self._methods['get_master']
            self.value = self._end.master
        elif self.request.method == self._methods['get_slaves']:
            self.method = self._methods['get_slaves']
            self.value = self._end.slaves

    def set_to_device(self, *args):
        if not self._end:
            raise ValueError("Slave server isn't defined.")

        if self.request.method == self._methods['set_master']:
            self.method = self._methods['set_master']

            if len(args) == 1:
                master, = args
            else:
                raise ValueError("Too much arguments.")
            self._end.config_request.set('enslave', 'mode', 'slave')
            self.value = self._end.config_request.set('enslave', 'master', master)
        elif self.request.method == self._methods['set_mode']:
            self.method = self._methods['set_mode']

            if len(args) == 1:
                mode, = args
            else:
                raise ValueError("Too much arguments.")
            self.value = self._end.config_request.set('enslave', 'mode', mode)
        else:
            raise ValueError('Unexcepted method: %s', self.request.method)

    def dump_config(self, *args):
        self.method = self._methods['dump']

        if not self._end:
            raise ValueError("Slave server isn't defined.")
        if len(args) == 1:
            section, = args
        else:
            section = None
        self.value = self._end.dump(str(section))

    def handle_register(self, *args):
        if not self._end:
            raise ValueError("Slave server isn't defined.")

        if self.request.method == self._methods['register_slave']:
            self.method = self._methods['register_slave']
            self.value = self._end.add_to_slaves()
        elif self.request.method == self._methods['unregister_slave']:
            self.method = self._methods['unregister_slave']
            self.value = self._end.remove_from_slaves()

    def handle(self):
        args = self.request.args
        try:
            if self.request.method & self._methods['set']:
                self.set_to_config(*args)
            elif self.request.method & self._methods['get']:
                self.get_from_device(*args)
            elif self.request.method & self._methods['dmp']:
                self.dump_config(*args)
            elif self.request.method & self._methods['reg']:
                self.handle_register(*args)
            else:
                raise ValueError('Unexcepted method: %s', self.request.method)

            return self.value
        except TimeoutError as e:
            raise e
        finally:
            return None
