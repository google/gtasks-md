# https://stackoverflow.com/a/69802572
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    UNKNOWN = "unknown"
    PENDING = "needsAction"
    COMPLETED = "completed"


# https://developers.google.com/tasks/reference/rest/v1/tasks
@dataclass
class Task:
    """Task definition matching Google Task API"""

    title: str
    id: str
    note: str
    position: int
    status: TaskStatus
    subtasks: list[Task]

    def __eq__(self, other: Task) -> bool:
        return (
            self.title == other.title
            and self.note == other.note
            and self.status == other.status
            and len(self.subtasks) == len(other.subtasks)
            and not any(st != ot for (st, ot) in zip(self.subtasks, other.subtasks))
        )

    def __str__(self) -> str:
        return f"#{self.position}: {self.title} ({self.id}): {self.status}, {len(self.subtasks)} subtasks"

    def completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    def toRequest(self) -> dict[str, str]:
        status = "needsAction"
        if self.status == TaskStatus.COMPLETED:
            status = "completed"

        return {
            "id": self.id,
            "kind": "tasks#task",
            "notes": self.note,
            "status": status,
            "title": self.title,
        }


# https://developers.google.com/tasks/reference/rest/v1/tasklists
@dataclass
class TaskList:
    """Tasklist definition matching Google Task API"""

    title: str
    id: str
    tasks: list[Task]

    def __eq__(self, other: TaskList) -> bool:
        return (
            self.title == other.title
            and len(self.tasks) == len(other.tasks)
            and not any(st != ot for (st, ot) in zip(self.tasks, other.tasks))
        )

    def __str__(self) -> str:
        return f"{self.title} ({self.id}): {len(self.tasks)} tasks"

    def toRequest(self) -> dict[str, str]:
        return {
            "id": self.id,
            "kind": "tasks#taskList",
            "title": self.title,
        }
