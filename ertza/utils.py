# -*- coding: utf-8 -*-

import sys, os
from queue import Empty

from ertza.base import BaseWorker
from ertza.config import ConfigParser
from ertza.errors import TimeoutError

import time
import signal
import functools

import logging
import logging.handlers

class LogWorker(BaseWorker):

    def __init__(self, sm):
        super(LogWorker, self).__init__(sm)
        self.config_pipe = self.initializer.cnf_log_pipe[1]
        from ertza.config import ConfigRequest
        self.config_request = ConfigRequest(self.config_pipe)

        f = '%(asctime)s %(processName)-10s %(levelname)-8s %(message)s'
        hf = logging.Formatter(f)
        root_logger = logging.getLogger()
        self.lg = root_logger

        self.wait_for_config()

        self.lg.debug(self.config_request.get('log', 'log_path'))
        self.log_path = self.config_request.get('log', 'log_path', 
                os.path.expanduser('~/.ertza/'))
        if not os.path.exists(self.log_path):
            self.exit('Log path must exist.')
        self.log_file = os.path.join(self.log_path, 'ertza.log')
        self.max_size = int(self.config_request.get('log', 'max_size',
                1048576))
        self.backup_count = int(self.config_request.get('log', 'backup_count',
                10))
        h = logging.handlers.RotatingFileHandler(self.log_file,
                maxBytes=self.max_size, backupCount=self.backup_count)

        logging.basicConfig(format=f)

        h.setFormatter(hf)
        root_logger.addHandler(h)

        self.run()

    def run(self):
        while not self.exit_event.is_set():
            try:
                record = self.lgq.get(timeout=0.1)
                if record is None: # We send this as a sentinel to tell the listener to quit.
                    break
                logger = logging.getLogger(record.name)
                logger.handle(record) # No level or filter logic applied - just do it!
            except Empty:
                pass
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                import traceback
                print('FATAL:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)


class FakeConfigParser(ConfigParser):
    def __init__(self):
        super(FakeConfigParser, self).__init__()

        self._conf_path = None
        self.save_path = None
        self.autosave = False
        self.read_hard_defaults()


class FakeConfig(object):
    def recv(self, *args):
        from ertza.config import ConfigResponse
        rp = ConfigResponse(self, self.rq, FakeConfigParser())

        rp.handle()
        rp.send()

        return rp

    def send(self, rq):
        self.rq = rq

def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.
    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):

        @functools.wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = "%s, Retrying in %d seconds... (%d/%d)" % \
                            (str(e), mdelay, tries-mtries+1, tries)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry

def timeout(seconds, error_message='Function call timed out'):
     def decorated(func):
         def _handle_timeout(signum, frame):
             raise TimeoutError(error_message)
 
         def wrapper(*args, **kwargs):
             signal.signal(signal.SIGALRM, _handle_timeout)
             signal.alarm(seconds)
             try:
                 result = func(*args, **kwargs)
             finally:
                 signal.alarm(0)
             return result
 
         return functools.wraps(func)(wrapper)
 
     return decorated
