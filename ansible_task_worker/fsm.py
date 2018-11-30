
from gevent_pipeline.fsm import State, transitions


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

        controller.changeState(Ready)


Initialize = _Initialize()


class _Start(State):

    @transitions('Waiting')
    def start(self, controller):

        controller.changeState(Waiting)


Start = _Start()


class _Waiting(State):

    @transitions('Initialize')
    def onInventory(self, controller, message_type, message):

        controller.changeState(Initialize)


Waiting = _Waiting()


class _End(State):


End = _End()


class _Ready(State):

    @transitions('Initialize')
    def onInventory(self, controller, message_type, message):

        controller.changeState(Initialize)

    @transitions('RunTask')
    def onTask(self, controller, message_type, message):

        controller.changeState(RunTask)


Ready = _Ready()
