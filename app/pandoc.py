# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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


def task_lists_to_markdown(task_lists: list[TaskList]) -> str:
    """Parses Task Lists to a Pandoc markdown"""

    def task_list_header_to_pandoc(task_list: TaskList) -> Header:
        match pandoc.read(task_list.title):
            case Pandoc(_, [Para(title)]):
                return Header(2, ("", [], []), title)
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
                        case Pandoc(_, []):
                            pass
                        case Pandoc(_, [*note]):
                            pandocTask += note
                        case _:
                            raise SyntaxError(
                                f"Could not parse Task note:\n{task.note}"
                            )
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
        Header(1, ("", [], []), [Str("Google"), Space(), Str("Tasks")]),
    ]

    for task_list in task_lists:
        content.append(task_list_header_to_pandoc(task_list))
        content.append(
            OrderedList(ORDERED_FIRST_ELEM, tasks_to_pandoc(task_list.tasks))
        )

    return pandoc.write(Pandoc(Meta({}), content))


def markdown_to_task_lists(text: str) -> list[TaskList]:
    """Parses Pandoc markdown to Task Lists"""

    def parse_task_lists(items, idx):
        if idx >= len(items):
            return []

        match items[idx]:
            case Header(1, _, _):
                return parse_task_lists(items, idx + 1)
            case Header(2, _, hd):
                task_list = TaskList("", pandoc.write(hd).strip(), [])

                if idx + 1 < len(items):
                    match items[idx + 1]:
                        case OrderedList(_, tasks):
                            task_list.tasks = parse_tasks(tasks)
                            return [task_list] + parse_task_lists(items, idx + 2)
                        case _:
                            return [task_list] + parse_task_lists(items, idx + 1)
                else:
                    return [task_list]
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
        subtasks = []
        match task[-1]:
            case OrderedList(_, subtasks):
                note = pandoc.write(
                    Pandoc(Meta({}), task[1:-1]), options=["--wrap=none"]
                )
                subtasks = parse_tasks(subtasks)
            case _:
                note = pandoc.write(Pandoc(Meta({}), task[1:]), options=["--wrap=none"])

        return Task("", name, note.strip(), taskNo, status, subtasks)

    match pandoc.read(text):
        case Pandoc(_, items):
            return parse_task_lists(items, 0)
        case _:
            raise SyntaxError("Expected Pandoc markdown representation.")
