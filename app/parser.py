# Copyright 2026 Google LLC
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
import re
import textwrap

import mdformat
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from .tasks import Task, TaskList, TaskStatus

# Renumber ordered lists consecutively (1. 2. 3.) instead of mdformat's
# default of repeating "1.".
MDFORMAT_OPTIONS = {"number": True}

CHECKBOX_REGEX = re.compile(r"^\[([ xX])\](?:[ \t]+|$)")


def task_lists_to_markdown(task_lists: list[TaskList]) -> str:
    """Renders Task Lists as a CommonMark document."""

    chunks = ["# Google Tasks"]
    for task_list in task_lists:
        chunks.append(f"## {task_list.title}")
        if task_list.tasks:
            chunks.append(_tasks_to_markdown(task_list.tasks))

    return mdformat.text("\n\n".join(chunks) + "\n", options=MDFORMAT_OPTIONS)


def markdown_to_task_lists(text: str) -> list[TaskList]:
    """Parses a CommonMark document into Task Lists."""

    root = SyntaxTreeNode(MarkdownIt().parse(text))
    lines = text.split("\n")

    task_lists: list[TaskList] = []
    after_task_list_header = False
    for node in root.children:
        if node.type == "heading" and node.tag == "h1":
            after_task_list_header = False
        elif node.type == "heading" and node.tag == "h2":
            task_lists.append(TaskList("", _inline_source(node), []))
            after_task_list_header = True
        elif node.type == "ordered_list" and after_task_list_header:
            task_lists[-1].tasks = _parse_tasks(node, lines)
            after_task_list_header = False
        else:
            raise SyntaxError(f"Unexpected item while parsing: {node.pretty()}")

    return task_lists


def _tasks_to_markdown(tasks: list[Task], indent: str = "") -> str:
    # Mirror the previous pandoc behavior: when any sibling has a note the
    # whole list is rendered loose (blank lines between items).
    loose = any(task.note for task in tasks)
    items = [
        _task_to_markdown(task, position + 1, indent, loose)
        for position, task in enumerate(tasks)
    ]
    return ("\n\n" if loose else "\n").join(items)


def _task_to_markdown(task: Task, number: int, indent: str, loose: bool) -> str:
    marker = f"{number}. "
    body_indent = indent + " " * len(marker)

    task_sign = "[x]" if task.completed() else "[ ]"
    lines = [f"{indent}{marker}{task_sign} {task.title}".rstrip()]

    if task.note:
        lines.append("")
        lines.extend((body_indent + line).rstrip() for line in task.note.splitlines())

    if task.subtasks:
        if loose or task.note:
            lines.append("")
        lines.append(_tasks_to_markdown(task.subtasks, body_indent))

    return "\n".join(lines)


def _parse_tasks(list_node: SyntaxTreeNode, lines: list[str]) -> list[Task]:
    return [
        _parse_task(item, position, lines)
        for position, item in enumerate(list_node.children)
    ]


def _parse_task(item: SyntaxTreeNode, position: int, lines: list[str]) -> Task:
    blocks = item.children
    if not blocks or blocks[0].type != "paragraph":
        raise SyntaxError(f"Expected Task status and title, got {item.pretty()}")

    title = _inline_source(blocks[0])
    status = TaskStatus.UNKNOWN
    if match := CHECKBOX_REGEX.match(title):
        status = TaskStatus.COMPLETED if match.group(1) in "xX" else TaskStatus.PENDING
        title = title[match.end() :].strip()

    blocks = blocks[1:]
    subtasks = []
    if blocks and blocks[-1].type == "ordered_list":
        subtasks = _parse_tasks(blocks[-1], lines)
        blocks = blocks[:-1]

    return Task("", title, _blocks_source(blocks, lines), position, status, subtasks)


def _inline_source(node: SyntaxTreeNode) -> str:
    """Verbatim markdown source of a heading or paragraph, as a single line."""

    if not node.children:
        return ""
    return re.sub(r"\s*\n\s*", " ", node.children[0].content).strip()


def _blocks_source(blocks: list[SyntaxTreeNode], lines: list[str]) -> str:
    """Verbatim markdown source of consecutive blocks, dedented."""

    if not blocks:
        return ""
    start, end = blocks[0].map[0], blocks[-1].map[1]
    return textwrap.dedent("\n".join(lines[start:end])).strip()
