import json
from enum import Enum, auto
from pprint import pprint

from googleapiclient.discovery import build

from .credentials import getCredentials
from .tasks import Task, TaskList, TaskStatus


# https://googleapis.github.io/google-api-python-client/docs/dyn/tasks_v1.html
class GoogleApiService:
    def __init__(self, credentials=getCredentials()):
        self._service = build("tasks", "v1", credentials=credentials)

    def reconcile(self, oldTasklists: list[TaskList], newTasklists: list[TaskList]):
        def gen_tasklist_ops():
            tasklistToOp = {}
            for tasklist in oldTasklists:
                tasklistToOp[tasklist.name] = (ReconcileOp.REMOVE, tasklist)

            for tasklist in newTasklists:
                if tasklist.name in tasklistToOp:
                    tasklistToOp[tasklist.name] = (
                        ReconcileOp.UPDATE,
                        tasklistToOp[tasklist.name][1],
                        tasklist,
                    )
                else:
                    tasklistToOp[tasklist.name] = (ReconcileOp.ADD, tasklist)

            return list(tasklistToOp.values())

        def apply_tasklist_ops(ops):
            for op in ops:
                match op:
                    case (ReconcileOp.REMOVE, tasklist):
                        self._service.tasklists().delete(tasklist=tasklist.id).execute()
                        print(f"REMOVED TASKLIST: {tasklist.name}")
                    case (ReconcileOp.ADD, tasklist):
                        self._service.tasklists().insert(
                            body=tasklist.toRequest()
                        ).execute()
                        print(f"ADDED TASKLIST: {tasklist.name}")
                    case (ReconcileOp.UPDATE, oldTasklist, newTasklist):
                        newTasks = apply_task_ops(
                            gen_task_ops(oldTasklist.tasks, newTasklist.tasks),
                            newTasklist.tasks,
                            oldTasklist.id,
                        )
                        fix_task_order(oldTasklist.id, newTasks, "")

        def gen_task_ops(oldTasks: list[Task], newTasks: list[Task]):
            taskToOp = {}
            for task in oldTasks:
                taskToOp[task.name] = (ReconcileOp.REMOVE, task)

            for i, task in enumerate(newTasks):
                if task.name in taskToOp:
                    taskToOp[task.name] = (
                        ReconcileOp.UPDATE,
                        taskToOp[task.name][1],
                        task,
                        i,
                    )
                else:
                    taskToOp[task.name] = (ReconcileOp.ADD, task, i)

            return list(taskToOp.values())

        def apply_task_ops(ops, newTasks, tasklistId):
            for op in ops:
                match op:
                    case (ReconcileOp.REMOVE, task):
                        self._service.tasks().delete(
                            tasklist=tasklistId, task=task.id
                        ).execute()
                        print(f"REMOVED TASK: {task.name}")
                    case (ReconcileOp.UPDATE, oldTask, newTask, idx):
                        newTasks[idx].id = oldTask.id

                        response = (
                            self._service.tasks()
                            .patch(
                                tasklist=tasklistId,
                                task=oldTask.id,
                                body=newTask.toRequest(),
                            )
                            .execute()
                        )

                        newSubtasks = apply_task_ops(
                            gen_task_ops(oldTask.subtasks, newTask.subtasks),
                            newTask.subtasks,
                            tasklistId,
                        )
                        fix_task_order(tasklistId, newSubtasks, oldTask.id)

                        newTasks[idx].subtasks = newSubtasks

                        print(f"UPDATED TASK: {newTask.name}")
                    case (ReconcileOp.ADD, task, idx):
                        response = (
                            self._service.tasks()
                            .insert(tasklist=tasklistId, body=task.toRequest())
                            .execute()
                        )
                        newTasks[idx].id = response["id"]
                        print(f"ADDED TASK: {task.name}")

            return newTasks

        def fix_task_order(tasklistId, tasks, parent):
            if len(tasks) > 0 and not tasks[0].completed():
                self._service.tasks().move(
                    tasklist=tasklistId,
                    task=tasks[0].id,
                    parent=parent,
                ).execute()

            for i in range(1, len(tasks)):
                if not tasks[i].completed():
                    self._service.tasks().move(
                        tasklist=tasklistId,
                        task=tasks[i].id,
                        parent=parent,
                        previous=tasks[i - 1].id,
                    ).execute()
                    print(
                        f"MOVED TASK {tasks[i].name} ({tasks[i].id}) after {tasks[i-1].name} ({tasks[i-1].id})"
                    )

        apply_tasklist_ops(gen_tasklist_ops())

    def get_tasklists(self) -> list[TaskList]:
        def get_tasks(taskList):
            result = (
                self._service.tasks()
                .list(tasklist=taskList, maxResults=100, showHidden=True)
                .execute()
            )

            tasks: dict[str, Task] = {}
            subtasks = []
            for task in result.get("items", []):
                parsedTask = parse_task(task)

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

        def parse_task(task):
            status = TaskStatus.UNKNOWN
            try:
                status = TaskStatus(task["status"])
            except:
                pass

            return Task(
                task["title"].strip(),
                task["id"],
                task.get("notes", ""),
                int(task["position"]),
                status,
                [],
            )

        result = self._service.tasklists().list(maxResults=100).execute()

        taskLists = []
        for taskList in result.get("items", []):
            id = taskList["id"]

            taskLists.append(TaskList(taskList["title"], id, get_tasks(id)))
        return taskLists


class ReconcileOp(Enum):
    ADD = auto()
    REMOVE = auto()
    UPDATE = auto()
