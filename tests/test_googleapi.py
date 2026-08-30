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
import asyncio
import threading
import unittest
from collections import defaultdict
from itertools import count

from app.googleapi import GoogleApiService
from app.tasks import Task, TaskList, TaskStatus


class FakeRequest:
    """Mimics googleapiclient's HttpRequest: a deferred call to the server."""

    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeBatchRequest:
    """Mimics BatchHttpRequest: executes requests and invokes callbacks."""

    def __init__(self):
        self._items = []

    def add(self, request, callback):
        self._items.append((request, callback))

    def execute(self):
        for request, callback in self._items:
            callback("", request.execute(), None)


class FakeTaskListsResource:
    def __init__(self, server):
        self._server = server

    def insert(self, body):
        return FakeRequest(lambda: self._server.insert_task_list(body))

    def delete(self, tasklist):
        return FakeRequest(lambda: self._server.delete_task_list(tasklist))


class FakeTasksResource:
    def __init__(self, server):
        self._server = server

    def insert(self, tasklist, body):
        return FakeRequest(lambda: self._server.insert_task(tasklist, body))

    def delete(self, tasklist, task):
        return FakeRequest(lambda: self._server.delete_task(tasklist, task))

    def patch(self, tasklist, task, body):
        return FakeRequest(lambda: self._server.patch_task(tasklist, task, body))

    def move(self, tasklist, task, parent, previous):
        return FakeRequest(
            lambda: self._server.move_task(tasklist, task, parent, previous)
        )


class FakeServer:
    """In-memory Google Tasks server holding task lists, tasks and ordering."""

    def __init__(self):
        self._ids = count()
        self._lock = threading.Lock()
        self.task_lists = {}  # task list id -> title
        self.tasks = {}  # task id -> {"title", "notes", "status", "parent"}
        # (task list id, parent task id or "") -> ordered task ids
        self.children = defaultdict(list)
        # Optional hook invoked at the start of every insert_task_list call.
        self.on_task_list_insert = None

    def insert_task_list(self, body):
        if self.on_task_list_insert:
            self.on_task_list_insert()
        with self._lock:
            id = f"tl{next(self._ids)}"
            self.task_lists[id] = body["title"]
            return {"id": id}

    def delete_task_list(self, tasklist):
        with self._lock:
            del self.task_lists[tasklist]
            return {}

    def insert_task(self, tasklist, body):
        with self._lock:
            id = f"t{next(self._ids)}"
            self.tasks[id] = {
                "title": body["title"],
                "notes": body.get("notes", ""),
                "status": body["status"],
                "parent": "",
            }
            self.children[(tasklist, "")].append(id)
            return {"id": id}

    def delete_task(self, tasklist, task):
        with self._lock:
            parent = self.tasks.pop(task)["parent"]
            self.children[(tasklist, parent)].remove(task)
            return {}

    def patch_task(self, tasklist, task, body):
        del tasklist
        with self._lock:
            self.tasks[task].update(
                title=body["title"], notes=body.get("notes", ""), status=body["status"]
            )
            return {"id": task}

    def move_task(self, tasklist, task, parent, previous):
        with self._lock:
            old_parent = self.tasks[task]["parent"]
            self.children[(tasklist, old_parent)].remove(task)
            siblings = self.children[(tasklist, parent)]
            position = siblings.index(previous) + 1 if previous else 0
            siblings.insert(position, task)
            self.tasks[task]["parent"] = parent
            return {"id": task}

    def snapshot(self) -> list[TaskList]:
        """Current server state as TaskLists sorted by title."""

        def to_task(tasklist, id, position):
            task = self.tasks[id]
            return Task(
                id,
                task["title"],
                task["notes"],
                position,
                TaskStatus(task["status"]),
                [
                    to_task(tasklist, sub_id, sub_position)
                    for sub_position, sub_id in enumerate(self.children[(tasklist, id)])
                ],
            )

        task_lists = [
            TaskList(
                id,
                title,
                [
                    to_task(id, task_id, position)
                    for position, task_id in enumerate(self.children[(id, "")])
                ],
            )
            for id, title in self.task_lists.items()
        ]
        return sorted(task_lists, key=lambda task_list: task_list.title)


class FakeGoogleApiService(GoogleApiService):
    """GoogleApiService whose API surface is backed by a FakeServer."""

    def __init__(self, server: FakeServer):
        super().__init__("test", None, None, "")
        self._server = server

    def tasks(self):
        return FakeTasksResource(self._server)

    def task_lists(self):
        return FakeTaskListsResource(self._server)

    def new_batch_http_request(self):
        return FakeBatchRequest()


class TestReconcile(unittest.TestCase):
    def setUp(self):
        self.server = FakeServer()
        self.service = FakeGoogleApiService(self.server)

    def reconcile(self, old_task_lists, new_task_lists):
        asyncio.run(self.service.reconcile(old_task_lists, new_task_lists))

    def seed(self, task_lists: list[TaskList]) -> list[TaskList]:
        """Loads task lists into the fake server, returning them with ids."""

        def seed_tasks(tasklist_id, tasks, parent_id):
            seeded = []
            previous_id = ""
            for position, task in enumerate(tasks):
                id = self.server.insert_task(tasklist_id, task.to_request())["id"]
                if parent_id:
                    self.server.move_task(tasklist_id, id, parent_id, previous_id)
                previous_id = id
                subtasks = seed_tasks(tasklist_id, task.subtasks, id)
                seeded.append(
                    Task(id, task.title, task.note, position, task.status, subtasks)
                )
            return seeded

        seeded = []
        for task_list in task_lists:
            id = self.server.insert_task_list({"title": task_list.title})["id"]
            seeded.append(
                TaskList(id, task_list.title, seed_tasks(id, task_list.tasks, ""))
            )
        return seeded

    def test_insert_task_list_with_tasks_and_subtasks(self):
        new_task_lists = [
            create_task_list(
                "Task List 1",
                create_task(
                    "Task 1",
                    note="Some note.",
                    subtasks=[create_task("Subtask 1"), create_task("Subtask 2")],
                ),
                create_task("Task 2"),
            )
        ]

        self.reconcile([], new_task_lists)

        self.assertEqual(self.server.snapshot(), new_task_lists)

    def test_delete_task_list(self):
        kept = create_task_list("Task List 1", create_task("Task 1"))
        deleted = create_task_list("Task List 2", create_task("Task 2"))
        old_task_lists = self.seed([kept, deleted])

        self.reconcile(old_task_lists, [kept])

        self.assertEqual(self.server.snapshot(), [kept])

    def test_update_tasks(self):
        old_task_lists = self.seed(
            [
                create_task_list(
                    "Task List 1",
                    create_task("Task 1"),
                    create_task("Task 2"),
                    create_task("Task 3"),
                )
            ]
        )
        # Task 1 is completed, Task 2 is deleted, Task 3 gets a note and moves
        # to the front, Task 4 is brand new. The completed task ends up last
        # because reconcile does not reorder completed tasks.
        new_task_lists = [
            create_task_list(
                "Task List 1",
                create_task("Task 3", note="Some note."),
                create_task("Task 4"),
                create_task("Task 1", status=TaskStatus.COMPLETED),
            )
        ]

        self.reconcile(old_task_lists, new_task_lists)

        self.assertEqual(self.server.snapshot(), new_task_lists)

    def test_reorder_tasks(self):
        task_list = create_task_list(
            "Task List 1",
            create_task("Task 1"),
            create_task("Task 2"),
            create_task("Task 3"),
        )
        old_task_lists = self.seed([task_list])
        new_task_lists = [
            create_task_list(
                "Task List 1",
                create_task("Task 3"),
                create_task("Task 1"),
                create_task("Task 2"),
            )
        ]

        self.reconcile(old_task_lists, new_task_lists)

        self.assertEqual(self.server.snapshot(), new_task_lists)

    def test_update_subtasks(self):
        old_task_lists = self.seed(
            [
                create_task_list(
                    "Task List 1",
                    create_task(
                        "Task 1",
                        subtasks=[create_task("Subtask 1"), create_task("Subtask 2")],
                    ),
                )
            ]
        )
        new_task_lists = [
            create_task_list(
                "Task List 1",
                create_task(
                    "Task 1",
                    subtasks=[
                        create_task("Subtask 2"),
                        create_task("Subtask 1"),
                        create_task("Subtask 3"),
                    ],
                ),
            )
        ]

        self.reconcile(old_task_lists, new_task_lists)

        self.assertEqual(self.server.snapshot(), new_task_lists)

    def test_task_lists_reconcile_concurrently(self):
        # Both task list inserts must be in flight at the same time to get
        # past the barrier. If reconcile ran them sequentially, the first
        # insert would time out and raise BrokenBarrierError.
        barrier = threading.Barrier(2, timeout=10)
        self.server.on_task_list_insert = barrier.wait
        new_task_lists = [
            create_task_list("Task List 1", create_task("Task 1")),
            create_task_list("Task List 2", create_task("Task 2")),
        ]

        self.reconcile([], new_task_lists)

        self.assertEqual(self.server.snapshot(), new_task_lists)


def create_task(
    title: str,
    note: str = "",
    status: TaskStatus = TaskStatus.PENDING,
    subtasks: list[Task] | None = None,
) -> Task:
    return Task("", title, note, 0, status, subtasks or [])


def create_task_list(title: str, *tasks: Task) -> TaskList:
    return TaskList("", title, list(tasks))


if __name__ == "__main__":
    unittest.main()
