
"""
Usage:
    ansible_task [options] <tasks-file>

Options:
    -h, --help        Show this page
    --debug            Show debug logging
    --verbose        Show verbose logging
"""
from docopt import docopt
import logging
import sys
import yaml
from .client import ZMQClientChannel
from .messages import Task
import gevent


logger = logging.getLogger('ansible_task')


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


    client = ZMQClientChannel()

    task_file = parsed_args['<tasks-file>']

    with open(task_file) as f:
        tasks = yaml.load(f.read())

    for task in tasks:
        print(task)
        client.send(Task(0, [task]))

    return 0
