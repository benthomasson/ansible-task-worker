
from gevent_fsm.fsm import State, transitions


class _Start(State):

    @transitions('Ready')
    def start(self, controller):

        controller.changeState(Ready)


Start = _Start()


class _Ready(State):

    def start(self, controller):
        print ("server_fsm buffered_messages", len(controller.context.buffered_messages))
        if not controller.context.buffered_messages.empty():
            controller.context.queue.put(controller.context.buffered_messages.get())

    @transitions('Waiting')
    def onTask(self, controller, message_type, message):

        controller.changeState(Waiting)
        controller.context.outbox.put(message)

    def onRunnerStdout(self, controller, message_type, message):
        pass

    def onRunnerMessage(self, controller, message_type, message):
        pass

    def onTaskComplete(self, controller, message_type, message):
        pass


Ready = _Ready()


class _Waiting(State):

    @transitions('Ready')
    def onTaskComplete(self, controller, message_type, message):

        controller.context.socket.send_multipart([message.client_id,
                                                  b'TaskComplete',
                                                  str(message.id).encode()])
        controller.changeState(Ready)

    def onRunnerStdout(self, controller, message_type, message):
        print (message)
        controller.context.socket.send_multipart([message.client_id,
                                                  b'RunnerStdout',
                                                  str(message.id).encode(),
                                                  message.data.encode()])

    def onRunnerMessage(self, controller, message_type, message):
        pass

Waiting = _Waiting()
