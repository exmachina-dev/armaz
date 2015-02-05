# -*- coding: utf-8 -*-

import sys
from queue import Empty

from ertza.base import BaseWorker

import logging
import logging.handlers

class LogWorker(BaseWorker):

    def __init__(self, sm):
        super(LogWorker, self).__init__(sm)
        f = '%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s'
        root_logger = logging.getLogger()
        logging.basicConfig(format=f)

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
