# https://stackoverflow.com/a/69802572
from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    UNKNOWN = "unknown"
    PENDING = "needsAction"
    COMPLETED = "completed"


@dataclass
class Task:
    name: str
    id: str
    text: str
    position: int
    status: TaskStatus
    subtasks: list[Task]

    def __str__(self):
        return f"#{self.position}: {self.name} ({self.id}): {self.status}, {len(self.subtasks)} subtasks"

    def completed(self):
        return self.status == TaskStatus.COMPLETED

    def toRequest(self):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        status = "needsAction"
        if self.status == TaskStatus.COMPLETED:
            status = "completed"

        return {
            "id": self.id,
            "kind": "tasks#task",
            "notes": self.text,
            "status": status,
            "title": self.name,
        }


@dataclass
class TaskList:
    name: str
    id: str
    tasks: list[Task]

    def __str__(self):
        return f"{self.name} ({self.id}): {len(self.tasks)} tasks"

    def debug(self):
        for task in self.tasks:
            print(f"  {task}")
            if task.text:
                formattedNote = task.text.replace("\n", "    \n")
                print(f"\n    {formattedNote}\n")
            for subtask in task.subtasks:
                print(f"    {subtask}")
                if subtask.text:
                    formattedNote = task.text.replace("\n", "      \n")
                    print(f"\n      {formattedNote}\n")

    def toRequest(self):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return {
            "id": self.id,
            "kind": "tasks#taskList",
            "title": self.name,
            "updated": now,
        }
