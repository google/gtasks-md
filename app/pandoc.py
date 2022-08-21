import pandoc
from pandoc import types

from .tasks import Task, TaskList, TaskStatus

# https://github.com/jgm/pandoc-types/blob/master/src/Text/Pandoc/Definition.hs
Decimal = types.Decimal  # type: ignore
Header = types.Header  # type: ignore
Meta = types.Meta  # type: ignore
OrderedList = types.OrderedList  # type: ignore
Pandoc = types.Pandoc  # type: ignore
Para = types.Para  # type: ignore
Period = types.Period  # type: ignore
Plain = types.Plain  # type: ignore
SoftBreak = types.SoftBreak  # type: ignore
Space = types.Space  # type: ignore
Str = types.Str  # type: ignore

ORDERED_FIRST_ELEM = (1, Decimal(), Period())


def toPandoc(taskLists: list[TaskList]) -> Pandoc:
    def taskListHeaderToPandoc(taskList: TaskList) -> Header:
        match pandoc.read(taskList.name):
            case Pandoc(_, [Para(name)]):
                return Header(2, ("", [], []), name)
            case _:
                return Header(2, ("", [], []), [Str("ERROR")])

    def taskListTasksToPandoc(taskList: TaskList):
        tasks = []
        hasNotes = any(t.text for t in taskList.tasks)
        for task in taskList.tasks:
            tasks.append(taskToPandoc(task, hasNotes))

        return tasks

    def taskToPandoc(task: Task, usePara: bool):
        pandocTask = []

        match pandoc.read(task.name):
            case Pandoc(_, [Para(name)]):
                sign = "☐"
                if task.status == TaskStatus.COMPLETED:
                    sign = "☒"
                str = [Str(sign), Space()] + name

                if usePara:
                    pandocTask.append(Para(str))
                    match pandoc.read(task.text):
                        case Pandoc(_, [notee]):
                            pandocTask.append(notee)
                        case Pandoc(_, []):
                            pass
                        case _:
                            pandocTask.append(Para([Str("ERROR")]))
                else:
                    pandocTask.append(Plain(str))
            case _:
                pandocTask.append(Plain([Str("ERROR")]))

        if task.subtasks:
            subtasks = []
            hasNotes = any(st.text for st in task.subtasks)
            for subtask in task.subtasks:
                subtasks.append(taskToPandoc(subtask, hasNotes))

            pandocTask.append(OrderedList(ORDERED_FIRST_ELEM, subtasks))

        return pandocTask

    content = [
        Header(1, ("todo", [], []), [Str("TODO")]),
    ]

    for taskList in taskLists:
        content.append(taskListHeaderToPandoc(taskList))
        content.append(OrderedList(ORDERED_FIRST_ELEM, taskListTasksToPandoc(taskList)))

    return Pandoc(Meta({}), content)
