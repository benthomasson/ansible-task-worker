
"""
Usage:
    ansible-cli [options] <output-playbook>

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

    def __init__(self, client, output, playbook):
        super(AnsibleCLI, self).__init__()
        self.counter = count()
        self.client = client
        self.output = output
        self.playbook = playbook

    def write_output_playbook(self):
        with open(self.output, 'w') as f:
            f.write(yaml.dump(self.playbook, default_flow_style=False))

    def do_EOF(self, line):
        raise KeyboardInterrupt()

    def do_e(self, line):
        self.do_edit(line)

    def do_edit(self, line):
        f, name = tempfile.mkstemp()
        os.close(f)
        Popen([EDITOR, name ]).wait()
        with open(name) as f:
            self.default(f.read())
        os.unlink(name)

    def default(self, line):
        self.playbook[0]['tasks'].append(yaml.safe_load(line))
        self.write_output_playbook()
        self.client.send(Task(next(self.counter), 0, [yaml.safe_load(line)]))
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

    output = parsed_args['<output-playbook>']
    playbook = [dict(name=parsed_args['<output-playbook>'],
                    hosts="localhost",
                    gather_facts=False,
                    tasks=[])]

    client = ZMQClientChannel()
    try:
        cli = AnsibleCLI(client, output, playbook)
        cli.cmdloop()
    except KeyboardInterrupt:
        pass

    return 0
