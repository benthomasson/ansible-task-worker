
"""
Usage:
    ansible-cli [options]

Options:
    -h, --help        Show this page
    --debug            Show debug logging
    --verbose        Show verbose logging
"""
from docopt import docopt
import logging
import os
import sys
from subprocess import Popen
import yaml
from .client import ZMQClientChannel
from .messages import Task
import cmd
from itertools import count
import distutils
import tempfile

EDITOR = distutils.spawn.find_executable(os.environ.get('EDITOR', 'vi'))


logger = logging.getLogger('ansible_task')


class AnsibleCLI(cmd.Cmd):

    def __init__(self, client):
        super(AnsibleCLI, self).__init__()
        self.counter = count()
        self.client = client

    def do_EOF(self, line):
        raise KeyboardInterrupt()

    def do_edit(self, line):
        f, name = tempfile.mkstemp()
        os.close(f)
        Popen([EDITOR, name ]).wait()
        with open(name) as f:
            self.default(f.read())
        os.unlink(name)

    def default(self, line):
        self.client.send(Task(next(self.counter), 0, [yaml.load(line)]))
        done = False
        while not done:
            msg = self.client.receive()
            if msg[0] == b'TaskComplete':
                done = True
            elif msg[0] == b'RunnerStdout':
                for line in msg[2].decode().splitlines():
                    print("{}: {}".format(msg[1].decode(), line))


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
    try:
        cli = AnsibleCLI(client)
        cli.cmdloop()
    except KeyboardInterrupt:
        pass

    return 0
