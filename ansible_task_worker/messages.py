
from collections import namedtuple
import yaml


def serialize(message):
    return [message.__class__.__name__.encode(), yaml.dump(dict(message._asdict())).encode()]


Task = namedtuple('Task', ['id', 'client_id', 'task'])
Inventory = namedtuple('Inventory', ['id', 'inventory'])
Cancel = namedtuple('Cancel', ['id', 'client_id'])
TaskComplete = namedtuple('TaskComplete', ['id', 'client_id'])
Error = namedtuple('Error', ['id', 'client_id'])
RunnerStdout = namedtuple('RunnerStdout', ['id', 'client_id', 'data'])
RunnerMessage = namedtuple('RunnerMessage', ['id', 'client_id', 'data'])
RunnerCancelled = namedtuple('RunnerCancelled', ['id', 'client_id'])
ShutdownComplete = namedtuple('ShutdownComplete', ['id', 'client_id'])
ShutdownRequested = namedtuple('ShutdownRequested', [])

StatusMessage = namedtuple('StatusMessage', ['message'])
TaskCompletionMessage = namedtuple('TaskCompletionMessage', ['task_num'])

msg_types = {x.__name__: x for x in [Task, Inventory]}
