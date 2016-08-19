# -*- coding: utf-8 -*-

from datetime import datetime


class OscFutureResult(object):
    def __init__(self, request):
        self._request = request
        self._send_time = datetime.now()
        self._reply_time = None

    @property
    def uuid(self):
        return self._request.uuid

    @property
    def request(self):
        return self._request

    @property
    def latency(self):
        '''
        Return the time between the instance initiation and the first call to
        latency.

        :returns: Latency value expressed in seconds
        '''

        if self._reply_time is None:
            self._reply_time = datetime.now()

        return (self._reply_time - self._send_time).microseconds / 1000

    def __eq__(self, other):
        try:
            if self.uuid == other.uuid:
                return True
            return False
        except AttributeError as e:
            raise TypeError('%s is not comparable with %s: %s' % (
                self.__class__.__name__, other.__class__.__name__, str(e)))

    def __repr__(self):
        return 'WF {}'.format(self.uuid)
