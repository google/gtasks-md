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


def task_lists_to_pandoc(task_lists: list[TaskList]) -> Pandoc:
    """Parses Task Lists to a Pandoc markdown representation"""

    def task_list_header_to_pandoc(task_list: TaskList) -> Header:
        match pandoc.read(task_list.title):
            case Pandoc(_, [Para(name)]):
                return Header(2, ("", [], []), name)
            case _:
                raise SyntaxError(f"Could not parse Task List title {task_list.title}")

    def tasks_to_pandoc(tasks: list[Task]):
        pandoc_tasks = []
        has_notes = any(t.note for t in tasks)
        for task in tasks:
            pandoc_tasks.append(task_to_pandoc(task, has_notes))

        return pandoc_tasks

    def task_to_pandoc(task: Task, use_para: bool):
        pandocTask = []

        match pandoc.read(task.title):
            case Pandoc(_, [Para(name)]):
                sign = "☒" if task.completed() else "☐"
                title = [Str(sign), Space()] + name

                if use_para:
                    pandocTask.append(Para(title))
                    match pandoc.read(task.note):
                        case Pandoc(_, [note]):
                            pandocTask.append(note)
                        case Pandoc(_, []):
                            pass
                        case _:
                            raise SyntaxError(f"Could not parse Task note {task.note}")
                else:
                    pandocTask.append(Plain(title))
            case _:
                raise SyntaxError(f"Could not parse Task title {task.title}")

        if task.subtasks:
            subtasks = []
            has_notes = any(st.note for st in task.subtasks)
            for subtask in task.subtasks:
                subtasks.append(task_to_pandoc(subtask, has_notes))

            pandocTask.append(OrderedList(ORDERED_FIRST_ELEM, subtasks))

        return pandocTask

    content = [
        Header(1, ("todo", [], []), [Str("TODO")]),
    ]

    for task_list in task_lists:
        content.append(task_list_header_to_pandoc(task_list))
        content.append(
            OrderedList(ORDERED_FIRST_ELEM, tasks_to_pandoc(task_list.tasks))
        )

    return Pandoc(Meta({}), content)


def pandoc_to_task_lists(doc: Pandoc) -> list[TaskList]:
    """Parses Pandoc markdown representation to Task Lists"""

    def parse_task_lists(items, idx):
        if idx >= len(items):
            return []

        match items[idx]:
            case Header(1, _, _):
                return parse_task_lists(items, idx + 1)
            case Header(2, _, hd):
                task_list = TaskList(pandoc.write(hd).strip(), "", [])
                match items[idx + 1]:
                    case OrderedList(_, tasks):
                        task_list.tasks = parse_tasks(tasks)
                        return [task_list] + parse_task_lists(items, idx + 2)
                    case _:
                        return [task_list] + parse_task_lists(items, idx + 1)
            case _:
                raise SyntaxError(f"Unexpected item while parsing: {items[idx]}")

    def parse_tasks(tasks):
        parsed_tasks = []

        for i, task in enumerate(tasks):
            parsed_tasks.append(parse_task(task, i))

        return parsed_tasks

    def parse_task(task, taskNo):
        def match_status(str: Str) -> TaskStatus:
            match str:
                case Str("☐"):
                    return TaskStatus.PENDING
                case Str("☒"):
                    return TaskStatus.COMPLETED
                case _:
                    raise SyntaxError(f"Expected status checkbox, got: ${str}")

        name = ""
        status = TaskStatus.UNKNOWN
        match task[0]:
            case Plain(txt):
                status = match_status(txt[0])
                name = pandoc.write(Plain(txt[2:])).strip()
            case Para(txt):
                status = match_status(txt[0])
                name = pandoc.write(Plain(txt[2:])).strip()
            case _:
                raise SyntaxError(f"Expected Task status and title, got {task[0]}")

        note = ""
        if len(task) > 1:
            match task[1]:
                case Plain(txt):
                    note = pandoc.write(Plain(txt)).strip()
                case Para(txt):
                    note = pandoc.write(Plain(txt)).strip()

        parsed_task = Task(name, "", note, taskNo, status, [])

        match task[-1]:
            case OrderedList(_, subtasks):
                parsed_task.subtasks = parse_tasks(subtasks)

        return parsed_task

    match doc:
        case Pandoc(_, items):
            return parse_task_lists(items, 0)
        case _:
            raise SyntaxError("Expected Pandoc markdown representation.")
