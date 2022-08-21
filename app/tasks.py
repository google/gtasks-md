from enum import Enum


class TaskList:
    def __init__(self, name, id, tasks):
        self.name: str = name
        self.id: str = id
        self.tasks: list[Task] = tasks
        pass

    def __str__(self):
        return f"{self.name} ({self.id}): {len(self.tasks)} tasks"

    def toPandoc(self):
        pass


class Task:
    def __init__(self, apiTask):
        self.name: str = apiTask["title"]
        self.id: str = apiTask["id"]
        self.text: str = apiTask.get("notes", "")
        self.position: int = int(apiTask["position"])
        self.subtasks: list[Task] = []

        try:
            self.status = TaskStatus(apiTask["status"])
        except:
            self.status = TaskStatus.UNKNOWN

    def __str__(self):
        return f"#{self.position}: {self.name} ({self.id}): {self.status}, {len(self.subtasks)} subtasks"


class TaskStatus(Enum):
    UNKNOWN = "unknown"
    PENDING = "needsAction"
    COMPLETED = "completed"
