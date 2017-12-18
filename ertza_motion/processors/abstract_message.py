# -*- coding: utf-8 -*-


class AbstractMessage(object):
    SEP = None
    protocol = ''

    def __init__(self, **kwargs):
        self.sender, self.receiver = None, None
        self.answer = None

        self.msg_type = kwargs['msg_type'] if 'msg_type' in kwargs else None

        self.sender = OscAddress(kwargs['sender']) if 'sender' in kwargs \
            else None
        self.receiver = OscAddress(kwargs['receiver']) if 'receiver' in kwargs \
            else None

    @property
    def command(self):
        raise NotImplementedError()

    @property
    def target(self):
        return self.command.split(self.SEP)[0]

    @property
    def args(self):
        raise NotImplementedError()

    @property
    def is_error(self):
        return self.command.split(self.SEP)[-1] == 'error'

    @property
    def is_ok(self):
        return self.command.split(self.SEP)[-1] == 'ok'

    @property
    def is_reply(self):
        return self.command.split(self.SEP)[-1] == 'reply'

    def __repr__(self):
        args = [str(i) for i in self.args]
        return '%s: %s %s' % (self.__class__.__name__, self.command,
                              ' '.join(args))
