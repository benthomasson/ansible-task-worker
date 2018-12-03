

import zmq
from .messages import serialize


class ZMQClientChannel(object):

    def __init__(self):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.connect('tcp://127.0.0.1:5555')

    def send(self, task):
        self.socket.send_multipart(serialize(task))
        msg = self.socket.recv_multipart()
        print (msg)
