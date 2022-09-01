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

    id: str
    title: str
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
        return {
            "id": self.id,
            "kind": "tasks#task",
            "notes": self.note,
            "status": self.status.value,
            "title": self.title,
        }


# https://developers.google.com/tasks/reference/rest/v1/tasklists
@dataclass
class TaskList:
    """Tasklist definition matching Google Task API"""

    id: str
    title: str
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
