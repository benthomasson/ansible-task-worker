
"""
Usage:
    ansible_task_server [options]

Options:
    -h, --help        Show this page
    --debug            Show debug logging
    --verbose        Show verbose logging
"""
from gevent import monkey
monkey.patch_all(thread=False)

from docopt import docopt
import logging
import sys
from .worker import AnsibleTaskWorker
from .server import ZMQServerChannel
import gevent
from .messages import Inventory
from .util import ConsoleTraceLog

logger = logging.getLogger('ansible_task_server')


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parsed_args = docopt(__doc__, args)
    if parsed_args['--debug']:
        logging.basicConfig(level=logging.DEBUG)
    elif parsed_args['--verbose']:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    tracer = ConsoleTraceLog()
    worker = AnsibleTaskWorker(tracer)
    server = ZMQServerChannel(worker.queue, tracer)
    server.outbox.put(Inventory(0, 'localhost ansible_connection=local'))
    worker.controller.outboxes['output'] = server.queue
    gevent.joinall([worker.thread, server.zmq_thread, server.controller_thread])
    return 0
