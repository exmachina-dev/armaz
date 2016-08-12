# -*- coding: utf-8 -*-

import logging
import time

logging = logging.getLogger('ertza.drivers.utils')


def retry(ExceptionToCatch, tries=3, wait=5, backoff=2):
    def decorator_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mwait, mbackoff = tries, wait, backoff
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCatch as e:
                    logging.error('Catched {!r}. Retrying in {} seconds...'
                                  .format(e, mwait))

                    time.sleep(mwait)
                    mtries -= 1
                    mwait *= mbackoff

            return f(*args, **kwargs)
        return f_retry
    return decorator_retry


def coroutine(func):
    def wrapper(*arg, **kwargs):
        generator = func(*arg, **kwargs)
        generator.send(None)
        return generator
    return wrapper
