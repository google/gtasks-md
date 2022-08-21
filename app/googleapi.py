from googleapiclient.discovery import build

from .credentials import getCredentials
from .tasks import Task, TaskList


class GoogleApiService:
    def __init__(self, credentials=getCredentials()):
        self._service = build("tasks", "v1", credentials=credentials)

    def getTaskLists(self) -> list[TaskList]:
        result = self._service.tasklists().list(maxResults=5).execute()

        taskLists = []
        for taskList in result.get("items", []):
            id = taskList["id"]

            taskLists.append(TaskList(taskList["title"], id, self._getTasks(id)))
        return taskLists

    def _getTasks(self, taskList):
        result = (
            self._service.tasks()
            .list(tasklist=taskList, maxResults=100, showHidden=True)
            .execute()
        )

        tasks: dict[str, Task] = {}
        subtasks = []
        for task in result.get("items", []):
            parsedTask = Task(task)

            parent = task.get("parent", "")
            if not parent:
                tasks[parsedTask.id] = parsedTask
            else:
                subtasks.append((parent, parsedTask))

        for subtask in subtasks:
            tasks[subtask[0]].subtasks.append(subtask[1])

        out: list[Task] = list(tasks.values())
        out.sort(key=lambda t: t.position)
        for task in out:
            task.subtasks.sort(key=lambda st: st.position)

        return out
