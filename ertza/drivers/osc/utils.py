# -*- coding: utf-8 -*-

class OscFutureResult(object):
    def __init__(self, request):
        self._request = request

    @property
    def uuid(self):
        return self._request.uuid

    @property
    def request(self):
        return self._request

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
