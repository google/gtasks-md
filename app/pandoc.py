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


def tasklists_to_pandoc(taskLists: list[TaskList]) -> Pandoc:
    def tasklist_header_to_pandoc(taskList: TaskList) -> Header:
        match pandoc.read(taskList.name):
            case Pandoc(_, [Para(name)]):
                return Header(2, ("", [], []), name)
            case _:
                return Header(2, ("", [], []), [Str("ERROR")])

    def tasklist_tasks_to_pandoc(taskList: TaskList):
        tasks = []
        hasNotes = any(t.text for t in taskList.tasks)
        for task in taskList.tasks:
            tasks.append(task_to_pandoc(task, hasNotes))

        return tasks

    def task_to_pandoc(task: Task, usePara: bool):
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
                subtasks.append(task_to_pandoc(subtask, hasNotes))

            pandocTask.append(OrderedList(ORDERED_FIRST_ELEM, subtasks))

        return pandocTask

    content = [
        Header(1, ("todo", [], []), [Str("TODO")]),
    ]

    for taskList in taskLists:
        content.append(tasklist_header_to_pandoc(taskList))
        content.append(
            OrderedList(ORDERED_FIRST_ELEM, tasklist_tasks_to_pandoc(taskList))
        )

    return Pandoc(Meta({}), content)


def pandoc_to_tasklists(doc: Pandoc) -> list[TaskList]:
    def parse_tasklists(items, idx):
        if idx >= len(items):
            return []

        match items[idx]:
            case Header(1, _, _):
                return parse_tasklists(items, idx + 1)
            case Header(2, _, hd):
                taskList = TaskList(pandoc.write(hd).strip(), "", [])
                match items[idx + 1]:
                    case OrderedList(_, tasks):
                        taskList.tasks = parse_tasks(tasks)
                        return [taskList] + parse_tasklists(items, idx + 2)
                    case _:
                        return [taskList] + parse_tasklists(items, idx + 1)
            case _:
                print("ERROR")
                exit(1)

    def parse_tasks(tasks):
        parsedTasks = []

        for i, task in enumerate(tasks):
            parsedTasks.append(parse_task(task, i))

        return parsedTasks

    def parse_task(task, taskNo):
        name = ""
        status = TaskStatus.UNKNOWN
        match task[0]:
            case Plain(txt):
                match txt[0]:
                    case Str("☐"):
                        status = TaskStatus.PENDING
                    case Str("☒"):
                        status = TaskStatus.COMPLETED
                name = pandoc.write(Plain(txt[2:])).strip()
            case Para(txt):
                match txt[0]:
                    case Str("☐"):
                        status = TaskStatus.PENDING
                    case Str("☒"):
                        status = TaskStatus.COMPLETED
                name = pandoc.write(Plain(txt[2:])).strip()
            case _:
                name = "UNKNOWN"

        note = ""
        if len(task) > 1:
            match task[1]:
                case Plain(txt):
                    note = pandoc.write(Plain(txt)).strip()
                case Para(txt):
                    note = pandoc.write(Plain(txt)).strip()

        parsedTask = Task(name, "", note, taskNo, status, [])

        match task[-1]:
            case OrderedList(_, subtasks):
                parsedTask.subtasks = parse_tasks(subtasks)

        return parsedTask

    match doc:
        case Pandoc(_, items):
            return parse_tasklists(items, 0)

    return []
