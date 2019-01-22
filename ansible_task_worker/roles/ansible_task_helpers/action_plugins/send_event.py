from ansible.plugins.action import ActionBase

import zmq
import yaml


class ActionModule(ActionBase):

    BYPASS_HOST_LOOP = True

    def run(self, tmp=None, task_vars=None):
        # print ('pause_for_kernel')
        if task_vars is None:
            task_vars = dict()
        host = self._task.args.get('host', None)
        port = self._task.args.get('port', None)
        to_fsm = self._task.args.get('to_fsm', None)
        from_fsm = self._task.args.get('from_fsm', None)
        event = self._task.args.get('event', None)
        data = self._task.args.get('data', {})
        # print (host)
        # print (port)
        # print (to_fsm)
        # print (from_fsm)
        # print (event)
        # print (data)
        # print (task_num)
        result = super(ActionModule, self).run(tmp, task_vars)

        context = zmq.Context()
        socket = context.socket(zmq.DEALER)
        socket.setsockopt(zmq.LINGER, 0)
        # print ('connecting...')
        socket.connect("tcp://{0}:{1}".format(host, port))
        # print ('connected')
        # print ('sending...')
        socket.send_multipart([b'Event', yaml.dump(dict(name=str(event),
                                                        to_fsm_id=str(to_fsm),
                                                        from_fsm_id=str(from_fsm),
                                                        data={})).encode()])
        # print ('sent')
        # print ('waiting...')
        socket.recv()
        # print ('received')
        # print ('closing...')
        socket.close()
        # print ('closed')
        return result
