import gevent
import zmq.green as zmq
from gevent.queue import Queue
from gevent_fsm.conf import settings
from gevent_fsm.fsm import FSMController, Channel, NullChannel
from . import worker_fsm
from . import messages
import ansible_runner
import tempfile
import os
import json
import yaml
import logging
import configparser
import pkg_resources
from .messages import StatusMessage


WORKSPACE = "/tmp/workspace"

logger = logging.getLogger("ansible_task_worker.consumers")


def ensure_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


settings.instrumented = True


class AnsibleTaskWorker(object):

    def __init__(self, tracer, fsm_id, inventory, play_header):
        self.tracer = tracer
        self.buffered_messages = Queue()
        self.controller = FSMController(self, "worker_fsm", fsm_id, worker_fsm.Start, self.tracer, self.tracer)
        self.controller.outboxes['default'] = Channel(self.controller, self.controller, self.tracer, self.buffered_messages)
        self.controller.outboxes['output'] = NullChannel(self.controller, self.tracer)
        self.queue = self.controller.inboxes['default']
        self.thread = gevent.spawn(self.controller.receive_messages)
        self.temp_dir = None
        self.cancel_requested = False
        self.task_id = None
        self.client_id = None
        self.key = None
        self.inventory = inventory
        self.status_socket_port = 0
        self.tasks_counter = 0
        self.next_task_file = None
        self.task_files = []
        self.play_header = play_header
        self.start_pause_handler()
        self.start_status_handler()
        self.initialize()
        self.start_play()

    def start_pause_handler(self):
        context = zmq.Context.instance()
        self.pause_queue = Queue()
        self.pause_socket = context.socket(zmq.REP)
        self.pause_socket_port = self.pause_socket.bind_to_random_port("tcp://127.0.0.1")
        self.recv_pause_thread = gevent.spawn(self.recv_pause)

    def stop_pause_handler(self):
        self.recv_pause_thread.kill()

    def start_status_handler(self):
        context = zmq.Context.instance()
        self.status_socket = context.socket(zmq.PULL)
        self.status_socket_port = self.status_socket.bind_to_random_port("tcp://127.0.0.1")
        self.recv_status_thread = gevent.spawn(self.recv_status)

    def stop_status_handler(self):
        self.recv_status_thread.kill()

    def recv_status(self):
        while True:
            msg = self.status_socket.recv_multipart()
            logger.info(msg)
            self.queue.put(StatusMessage(json.loads(msg[0])))
            gevent.sleep()

    def recv_pause(self):
        while True:
            msg = self.pause_socket.recv_multipart()
            logger.info("completed %s waiting...", msg)
            self.queue.put(messages.TaskComplete(self.task_id, self.client_id))
            self.pause_queue.get()
            logger.info('Sending Proceed')
            self.pause_socket.send_string('Proceed')
            logger.info('Sent Proceed')
            gevent.sleep()

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
        self.write_ansible_cfg()

    def write_ansible_cfg(self):
        config = configparser.SafeConfigParser()
        if not os.path.exists(os.path.join(self.temp_dir, 'project')):
            os.mkdir(os.path.join(self.temp_dir, 'project'))

        if not config.has_section('defaults'):
            config.add_section('defaults')
        config.set('defaults', 'fact_caching', 'jsonfile')
        config.set('defaults', 'fact_caching_connection', 'fact_cache')
        if config.has_option('defaults', 'roles_path'):
            roles_path = config.get('defaults', 'roles_path')
            roles_path = ":".join([os.path.abspath(x) for x in roles_path.split(":")])
            roles_path = "{0}:{1}".format(roles_path,
                                          os.path.abspath(pkg_resources.resource_filename('ansible_task_worker', 'roles')))
            config.set('defaults', 'roles_path', roles_path)
        else:
            config.set('defaults', 'roles_path', os.path.abspath(
                pkg_resources.resource_filename('ansible_task_worker', 'roles')))
        if not config.has_section('callback_ansible_worker_helper'):
            config.add_section('callback_ansible_worker_helper')
        config.set('callback_ansible_worker_helper',
                   'status_port', str(self.status_socket_port))
        with open(os.path.join(self.temp_dir, 'project', 'ansible.cfg'), 'w') as f:
            config.write(f)
        logger.info("Wrote ansible.cfg")

    def add_inventory(self, inventory):
        with open(os.path.join(self.temp_dir, 'inventory'), 'w') as f:
            f.write("\n".join(inventory.splitlines()))

    def add_keys(self, key):
        with open(os.path.join(self.temp_dir, 'env', 'ssh_key'), 'w') as f:
            f.write(key)

    def add_playbook(self, playbook):
        playbook_file = (os.path.join(self.temp_dir, 'project', 'playbook.yml'))
        with open(playbook_file, 'w') as f:
            f.write(yaml.safe_dump(playbook, default_flow_style=False))

    def run_playbook(self):
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
        self.controller.outboxes['output'].put(messages.RunnerStdout(self.task_id, self.client_id, data.get('stdout', '')))
        self.controller.outboxes['output'].put(messages.RunnerMessage(self.task_id, self.client_id, data))

    def cancel_callback(self):
        return self.cancel_requested

    def finished_callback(self, runner):
        logger.info('called')
        self.queue.put(messages.PlaybookFinished(self.task_id, self.client_id))
        self.controller.outboxes['output'].put(messages.PlaybookFinished(self.task_id, self.client_id))

    def initialize(self):
        try:
            self.build_project_directory()
            if self.key:
                self.add_keys(self.key)
            if self.inventory:
                self.add_inventory(self.inventory)
        except BaseException as e:
            logger.error(str(e))

    def build_play(self):
        current_play = self.play_header.copy()
        current_play['roles'] = current_play.get('roles', [])
        current_play['roles'].insert(0, 'ansible_task_helpers')
        tasks = current_play['tasks'] = current_play.get('tasks', [])
        tasks.append({'pause_for_kernel': {'host': '127.0.0.1',
                                           'port': self.pause_socket_port,
                                           'task_num': self.tasks_counter - 1}})
        tasks.append(
            {'include_tasks': 'next_task{0}.yml'.format(self.tasks_counter)})
        return current_play

    def start_play(self):
        try:
            self.add_playbook([self.build_play()])
            self.run_playbook()
        except BaseException as e:
            logger.error(str(e))

    def run_task(self, message):
        self.current_task = message
        try:
            tasks = []
            current_task_data = message.task[0].copy()
            current_task_data['ignore_errors'] = True
            tasks.append(current_task_data)
            tasks.append({'pause_for_kernel': {'host': '127.0.0.1',
                                               'port': self.pause_socket_port,
                                               'task_num': self.tasks_counter}})
            tasks.append(
                {'include_tasks': 'next_task{0}.yml'.format(self.tasks_counter + 1)})

            self.next_task_file = os.path.join(self.temp_dir, 'project',
                                               'next_task{0}.yml'.format(self.tasks_counter))
            self.tasks_counter += 1
            self.task_files.append(self.next_task_file)
            with open(self.next_task_file, 'w') as f:
                f.write(yaml.safe_dump(tasks, default_flow_style=False))
            self.pause_queue.put("Proceed")
        except BaseException as e:
            logger.error(str(e))
