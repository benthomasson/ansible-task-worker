
from gevent_fsm.fsm import State, transitions
from queue import Empty
from . import messages


class _RunTask(State):

    @transitions('ShuttingDown')
    def onShutdownRequested(self, controller, message_type, message):
        controller.changeState(ShuttingDown)

    @transitions('TaskComplete')
    def onStatus(self, controller, message_type, message):

        controller.changeState(TaskComplete)

    @transitions('TaskComplete')
    def onTaskComplete(self, controller, message_type, message):

        task_id = controller.context.task_id
        client_id = controller.context.client_id
        controller.changeState(TaskComplete)
        controller.outboxes['output'].put(messages.TaskComplete(task_id, client_id))


RunTask = _RunTask()


class _TaskComplete(State):

    @transitions('ShuttingDown')
    def onShutdownRequested(self, controller, message_type, message):
        controller.changeState(ShuttingDown)

    @transitions('Ready')
    def start(self, controller):

        controller.changeState(Ready)


TaskComplete = _TaskComplete()


class _Initialize(State):

    @transitions('Ready')
    def start(self, controller):

        controller.changeState(Ready)


Initialize = _Initialize()


class _Start(State):

    @transitions('Waiting')
    def start(self, controller):

        controller.changeState(Waiting)


Start = _Start()


class _Waiting(State):

    @transitions('Initialize')
    def onTaskComplete(self, controller, message_type, message):
        controller.changeState(Initialize)


Waiting = _Waiting()

class _ShuttingDown(State):

    def start(self, controller):
        controller.context.cancel_requested = True

    @transitions('End')
    def onTaskComplete(self, controller, message_type, message):
        controller.changeState(End)


ShuttingDown = _ShuttingDown()

class _End(State):

    def start(self, controller):
        task_id = controller.context.task_id
        client_id = controller.context.client_id
        controller.outboxes['output'].put(messages.ShutdownComplete(task_id, client_id))

End = _End()


class _Ready(State):

    @transitions('ShuttingDown')
    def onShutdownRequested(self, controller, message_type, message):
        controller.changeState(ShuttingDown)

    def start(self, controller):
        print ("worker_fsm buffered_messages", len(controller.context.buffered_messages))
        try:
            while True:
                message = controller.context.buffered_messages.get_nowait()
                print (message)
                controller.context.queue.put(message)
        except Empty:
            pass

    def onInventory(self, controller, message_type, message):
        pass

    @transitions('RunTask')
    def onTask(self, controller, message_type, message):

        controller.changeState(RunTask)
        controller.context.task_id = message.id
        controller.context.client_id = message.client_id
        controller.context.run_task(message)


Ready = _Ready()
