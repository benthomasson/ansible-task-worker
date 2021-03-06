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

    @transitions('Restart')
    def onPlaybookFinished(self, controller, message_type, message):
        controller.changeState(Restart)


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

    @transitions('End')
    def onPlaybookFinished(self, controller, message_type, message):
        controller.changeState(End)


Waiting = _Waiting()


class _ShuttingDown(State):

    def start(self, controller):
        controller.context.cancel_requested = True

    @transitions('End')
    def onTaskComplete(self, controller, message_type, message):
        controller.changeState(End)

    @transitions('End')
    def onPlaybookFinished(self, controller, message_type, message):
        controller.changeState(End)


ShuttingDown = _ShuttingDown()


class _End(State):

    def start(self, controller):
        task_id = controller.context.task_id
        client_id = controller.context.client_id
        controller.outboxes['output'].put(messages.ShutdownComplete(task_id, client_id))

    def onShutdownRequested(self, controller, message_type, message):
        task_id = controller.context.task_id
        client_id = controller.context.client_id
        controller.outboxes['output'].put(messages.ShutdownComplete(task_id, client_id))

    def onTaskComplete(self, controller, message_type, message):
        task_id = controller.context.task_id
        client_id = controller.context.client_id
        controller.outboxes['output'].put(messages.ShutdownComplete(task_id, client_id))

    def onPlaybookFinished(self, controller, message_type, message):
        task_id = controller.context.task_id
        client_id = controller.context.client_id
        controller.outboxes['output'].put(messages.ShutdownComplete(task_id, client_id))


End = _End()


class _Ready(State):

    @transitions('ShuttingDown')
    def onShutdownRequested(self, controller, message_type, message):
        controller.changeState(ShuttingDown)

    def start(self, controller):
        try:
            while True:
                message = controller.context.buffered_messages.get_nowait()
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

    @transitions('Restart')
    def onPlaybookFinished(self, controller, message_type, message):
        controller.changeState(Restart)


Ready = _Ready()


class _Restart(State):

    @transitions('Waiting')
    def start(self, controller):

        controller.context.stop_pause_handler()
        controller.context.stop_status_handler()
        controller.context.start_pause_handler()
        controller.context.start_status_handler()
        controller.context.start_play()
        controller.changeState(Waiting)
        controller.context.queue.put(controller.context.current_task)


Restart = _Restart()
