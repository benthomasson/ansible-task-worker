
from collections import namedtuple
import yaml


def serialize(message):
    return [message.__class__.__name__.encode(), yaml.dump(dict(message._asdict())).encode()]

Task = namedtuple('Task', ['id', 'task'])
Inventory = namedtuple('Inventory', ['id', 'inventory'])
Cancel = namedtuple('Cancel', ['id'])
TaskComplete = namedtuple('TaskComplete', ['id'])
Error = namedtuple('Error', ['id'])
RunnerStdout = namedtuple('RunnerStdout', ['id', 'data'])
RunnerMessage = namedtuple('RunnerMessage', ['id', 'data'])
RunnerCancelled = namedtuple('RunnerCancelled', ['id'])

msg_types = {x.__name__: x for x in [Task, Inventory]}
