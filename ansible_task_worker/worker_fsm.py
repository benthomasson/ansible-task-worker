
from gevent_fsm.fsm import State, transitions


class _RunTask(State):

    @transitions('End')
    def onShutdown(self, controller, message_type, message):

        controller.changeState(End)

    @transitions('TaskComplete')
    def onStatus(self, controller, message_type, message):

        controller.changeState(TaskComplete)

    @transitions('TaskComplete')
    def onTaskComplete(self, controller, message_type, message):

        controller.changeState(TaskComplete)


RunTask = _RunTask()


class _TaskComplete(State):

    @transitions('Ready')
    def start(self, controller):

        controller.changeState(Ready)


TaskComplete = _TaskComplete()


class _Initialize(State):

    @transitions('Ready')
    def start(self, controller):

        controller.context.initialize()
        controller.changeState(Ready)


Initialize = _Initialize()


class _Start(State):

    @transitions('Waiting')
    def start(self, controller):

        controller.changeState(Waiting)


Start = _Start()


class _Waiting(State):

    def start(self, controller):
        print ("worker_fsm buffered_messages", len(controller.context.buffered_messages))
        if not controller.context.buffered_messages.empty():
            controller.context.queue.put(controller.context.buffered_messages.get())

    @transitions('Initialize')
    def onInventory(self, controller, message_type, message):
        controller.context.inventory = message.inventory
        controller.changeState(Initialize)

    @transitions('Initialize')
    def onKey(self, controller, message_type, message):
        controller.context.key = message.key
        controller.changeState(Initialize)


Waiting = _Waiting()


class _End(State):

    pass


End = _End()


class _Ready(State):

    @transitions('Initialize')
    def onInventory(self, controller, message_type, message):

        controller.changeState(Initialize)
        controller.handle_message(message_type, message)

    @transitions('Initialize')
    def onKey(self, controller, message_type, message):

        controller.changeState(Initialize)
        controller.handle_message(message_type, message)

    @transitions('RunTask')
    def onTask(self, controller, message_type, message):

        controller.changeState(RunTask)
        controller.context.task_id = message.id
        controller.context.client_id = message.client_id
        controller.context.run_task(message)


Ready = _Ready()
