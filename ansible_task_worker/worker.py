import gevent
from gevent.queue import Queue
from gevent_fsm.conf import settings
from gevent_fsm.fsm import FSMController, Channel, NullChannel
from . import worker_fsm
from . import messages
from itertools import count
import ansible_runner
import tempfile
import os
import json
import yaml
import logging
import traceback


WORKSPACE = "/tmp/workspace"

logger = logging.getLogger("ansible_worker_channels.consumers")


def ensure_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


settings.instrumented = True


class AnsibleTaskWorker(object):

    def __init__(self):
        self.counter = count(start=1, step=1)
        self.buffered_messages = Queue()
        self.controller = FSMController(self, "worker_fsm", 1, worker_fsm.Start, self, self)
        self.controller.outboxes['default'] = Channel(self.controller, self.controller, self, self.buffered_messages)
        self.controller.outboxes['output'] = NullChannel(self.controller, self)
        self.queue = self.controller.inboxes['default']
        self.thread = gevent.spawn(self.controller.receive_messages)
        self.temp_dir = None
        self.cancel_requested = False
        self.task_id = None
        self.key = None
        self.inventory = None

    def trace_order_seq(self):
        return next(self.counter)

    def send_trace_message(self, message):
        print(message)

    def build_project_directory(self):
        ensure_directory(WORKSPACE)
        self.temp_dir = tempfile.mkdtemp(prefix="ansible_worker", dir=WORKSPACE)
        logger.info("temp_dir %s", self.temp_dir)
        ensure_directory(os.path.join(self.temp_dir, 'env'))
        ensure_directory(os.path.join(self.temp_dir, 'project'))
        ensure_directory(os.path.join(self.temp_dir, 'project', 'roles'))
        with open(os.path.join(self.temp_dir, 'env', 'settings'), 'w') as f:
            f.write(json.dumps(dict(idle_timeout=0,
                                    job_timeout=0)))

    def add_inventory(self, inventory):
        print("add_inventory")
        with open(os.path.join(self.temp_dir, 'inventory'), 'w') as f:
            f.write("\n".join(inventory.splitlines()))

    def add_keys(self, key):
        print("add_keys")
        with open(os.path.join(self.temp_dir, 'env', 'ssh_key'), 'w') as f:
            f.write(key)

    def add_playbook(self, playbook):
        print("add_playbook")
        playbook_file = (os.path.join(self.temp_dir, 'project', 'playbook.yml'))
        with open(playbook_file, 'w') as f:
            f.write(yaml.safe_dump(playbook, default_flow_style=False))

    def run_playbook(self):
        print("run_playbook")
        print(str(self.temp_dir))
        gevent.spawn(ansible_runner.run,
                     private_data_dir=self.temp_dir,
                     playbook="playbook.yml",
                     quiet=False,
                     debug=True,
                     ignore_logging=True,
                     cancel_callback=self.cancel_callback,
                     finished_callback=self.finished_callback,
                     event_handler=self.runner_process_message)

    def runner_process_message(self, data):
        self.controller.outboxes['output'].put(messages.RunnerStdout(self.task_id, data.get('stdout', '')))
        self.controller.outboxes['output'].put(messages.RunnerMessage(self.task_id, data))

    def cancel_callback(self):
        return self.cancel_requested

    def finished_callback(self, runner):
        logger.info('called')
        self.queue.put(messages.TaskComplete(self.task_id))

    def initialize(self):
        try:
            self.build_project_directory()
            if self.key:
                self.add_keys(self.key)
            if self.inventory:
                self.add_inventory(self.inventory)
        except BaseException as e:
            print(str(e))
            print(traceback.format_exc())
            logger.error(str(e))

    def run_task(self, message):
        try:
            task = message.task
            self.add_playbook(task)
            self.run_playbook()
        except BaseException as e:
            print(str(e))
            print(traceback.format_exc())
            logger.error(str(e))
