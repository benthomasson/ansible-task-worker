import zmq.green as zmq
from .messages import serialize, msg_types
import gevent
import yaml

class ZMQServerChannel(object):

    def __init__(self, outbox):
        self.outbox = outbox
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind('tcp://127.0.0.1:5555')
        self.thread = gevent.spawn(self.receive_messages)

    def receive_messages(self):
        while True:
            message = self.socket.recv_multipart()
            id = message.pop(0)
            msg_type = message.pop(0).decode()
            msg_data = yaml.load(message.pop(0).decode())
            print (id, msg_type, msg_data)
            msg_data['id'] = id
            self.outbox.put(msg_types[msg_type](**msg_data))
            self.socket.send_multipart([id, b'Hi'])

