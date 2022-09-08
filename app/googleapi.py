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
import asyncio
import logging
import os
from collections import defaultdict
from datetime import datetime
from enum import Enum, auto

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from xdg import xdg_cache_home, xdg_data_home

from .tasks import Task, TaskList, TaskStatus

CREDENTIALS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/tasks"]


# https://googleapis.github.io/google-api-python-client/docs/dyn/tasks_v1.html
class GoogleApiService:
    def __init__(
        self,
        user: str,
        completed_after: datetime | None,
        completed_before: datetime | None,
        task_status: TaskStatus,
    ):
        self.user = user
        self.completed_after = completed_after
        self.completed_before = completed_before
        self.task_status = TaskStatus(task_status) if task_status else None
        self._service = None

    def tasks(self):
        return self._get_service().tasks()

    def task_lists(self):
        return self._get_service().tasklists()

    def new_batch_http_request(self):
        return self._get_service().new_batch_http_request()

    async def reconcile(
        self, old_task_lists: list[TaskList], new_task_lists: list[TaskList]
    ):
        """
        Reconciles differences between new and old task lists.

        After a user modifies state containing all tasklists with their tasks,
        it's needed to reconcile resulting differences. The logic for task
        lists, tasks and subtasks is somewhat similar. At first all the old
        task lists are marked to be removed. Then for every new task lists if
        it's ID was set to be removed then it's reconciled (updated) instead.
        Otherwise such task list is marked to be added. In the end the order of
        items is restored. Items that have the same old and new state are
        skipped. All the items are matched based on title.
        """

        def gen_tasklist_ops():
            task_list_to_op = {}
            for task_list in old_task_lists:
                task_list_to_op[task_list.title] = (ReconcileOp.DELETE, task_list)

            for task_list in new_task_lists:
                if task_list.title in task_list_to_op:
                    task_list_to_op[task_list.title] = (
                        ReconcileOp.UPDATE,
                        task_list_to_op[task_list.title][1],
                        task_list,
                    )
                else:
                    task_list_to_op[task_list.title] = (ReconcileOp.INSERT, task_list)

            return list(task_list_to_op.values())

        async def apply_task_list_op(op):
            match op:
                case (ReconcileOp.DELETE, task_list):
                    self.task_lists().delete(tasklist=task_list.id).execute()
                    logging.info(f"Deleted Task List {task_list.title}")

                case (ReconcileOp.INSERT, task_list):
                    response = (
                        self.task_lists().insert(body=task_list.toRequest()).execute()
                    )
                    reconcile_tasks(response["id"], [], task_list.tasks)
                    logging.info(f"Inserted Task List {task_list.title}")

                case (ReconcileOp.UPDATE, old_task_list, new_task_list):
                    if old_task_list != new_task_list:
                        reconcile_tasks(
                            old_task_list.id, old_task_list.tasks, new_task_list.tasks
                        )
                        logging.info(f"Updated Task List {old_task_list.title}")

        def reconcile_tasks(task_list_id, old_tasks, new_tasks, parent_task_id=""):
            updated_tasks = apply_task_ops(
                gen_task_ops(old_tasks, new_tasks),
                new_tasks,
                task_list_id,
            )

            completed_tasks = []
            incompleted_tasks = []
            for task in updated_tasks:
                if task.completed():
                    completed_tasks.append(task)
                else:
                    incompleted_tasks.append(task)
            fix_task_order(
                task_list_id,
                list(incompleted_tasks),
                parent_task_id,
            )
            fix_task_order(
                task_list_id,
                list(completed_tasks),
                parent_task_id,
            )
            return updated_tasks

        def apply_task_ops(ops, new_tasks, task_list_id):
            def delete_callback(task_title):
                def callback(request_id, response, exception):
                    del request_id, response
                    if exception:
                        logging.error(f"Failed to delete task {task_title}")
                    else:
                        logging.info(f"Deleted Task {task_title}")

                return callback

            def insert_callback(task, idx):
                def callback(_, response, exception):
                    if exception:
                        logging.error(f"Failed to insert task {task.title}")

                    task_id = response["id"]
                    new_tasks[idx].id = task_id  # Needed for fix_task_order

                    updated_subtasks = reconcile_tasks(
                        task_list_id, [], task.subtasks, task_id
                    )
                    new_tasks[idx].subtasks = updated_subtasks
                    logging.info(f"Inserted Task {task.title}")

                return callback

            def update_callback(old_task, new_task, idx):
                def callback(request_id, response, exception):
                    del request_id, response
                    if exception:
                        logging.error(f"Failed to update Task {old_task.title}")
                        return

                    updated_subtasks = reconcile_tasks(
                        task_list_id, old_task.subtasks, new_task.subtasks, old_task.id
                    )
                    new_tasks[idx].subtasks = updated_subtasks
                    logging.info(f"Updated Task {old_task.title}")

                return callback

            batched_request = self.new_batch_http_request()
            for op in ops:
                match op:
                    case (ReconcileOp.DELETE, task):
                        batched_request.add(
                            self.tasks().delete(tasklist=task_list_id, task=task.id),
                            delete_callback(task.title),
                        )
                    case (ReconcileOp.INSERT, task, idx):
                        batched_request.add(
                            self.tasks().insert(
                                tasklist=task_list_id, body=task.toRequest()
                            ),
                            insert_callback(task, idx),
                        )
                    case (ReconcileOp.UPDATE, old_task, new_task, idx):
                        new_tasks[idx].id = old_task.id  # Needed for fix_task_order
                        if old_task != new_task:
                            batched_request.add(
                                self.tasks().patch(
                                    tasklist=task_list_id,
                                    task=old_task.id,
                                    body=new_task.toRequest(),
                                ),
                                update_callback(old_task, new_task, idx),
                            )
            batched_request.execute()

            return new_tasks

        def gen_task_ops(old_tasks: list[Task], new_tasks: list[Task]):
            task_to_op = {}
            for task in old_tasks:
                task_to_op[task.title] = (ReconcileOp.DELETE, task)

            for i, task in enumerate(new_tasks):
                if task.title in task_to_op:
                    task_to_op[task.title] = (
                        ReconcileOp.UPDATE,
                        task_to_op[task.title][1],
                        task,
                        i,
                    )
                else:
                    task_to_op[task.title] = (ReconcileOp.INSERT, task, i)

            return list(task_to_op.values())

        # The move requests can't be sent in parallel as there must not be
        # two values pointing to the same predecessor.
        def fix_task_order(task_list_id, new_tasks, parent_task_id=""):
            for i, task in enumerate(new_tasks):
                previous_task = new_tasks[i - 1] if i > 0 else None
                previous_task_id = previous_task.id if previous_task else ""

                self.tasks().move(
                    tasklist=task_list_id,
                    task=task.id,
                    parent=parent_task_id,
                    previous=previous_task_id,
                ).execute()

                previous_task_title = previous_task.title if previous_task else "NONE"
                logging.info(
                    f"Moved task {task.title} after {previous_task_title} (parent: {parent_task_id})"
                )

        async_tasks = []
        for op in gen_tasklist_ops():
            async_tasks.append(asyncio.create_task(apply_task_list_op(op)))
        await asyncio.gather(*async_tasks)

    def fetch_task_lists(self) -> list[TaskList]:
        """
        Fetches all tasks from the server.

        At first the function fetches up to 100 task lists. Then it fetches all
        tasks for these task lists that are either completed at most 30 days ago
        or are still pending completion.
        """
        id_to_task_list = {}
        task_id_to_subtasks = defaultdict(list)

        def create_request_with_callback(task_list_id, completed):
            def fetch_tasks_request(task_list_id, completed, next_page_token=""):
                completed_max = ""
                completed_min = ""
                if completed:
                    if self.completed_before:
                        completed_max = self.completed_before.isoformat()
                    if self.completed_after:
                        completed_min = self.completed_after.isoformat()

                return self.tasks().list(
                    completedMax=completed_max,
                    completedMin=completed_min,
                    maxResults=100,
                    pageToken=next_page_token,
                    showCompleted=completed,
                    showHidden=completed,
                    tasklist=task_list_id,
                )

            def callback(_, response, exception):
                if exception:
                    logging.error(
                        f"Error on fetching Tasks from Task List {task_list_id}: {exception}"
                    )
                    return

                fetched_tasks = response.get("items", [])
                next_page_token = response.get("nextPageToken", "")
                while next_page_token:
                    response = fetch_tasks_request(
                        task_list_id, completed, next_page_token
                    )
                    fetched_tasks += response.get("items", [])
                    next_page_token = response.get("nextPageToken", "")

                for fetched_task in fetched_tasks:
                    task = Task(
                        fetched_task["id"],
                        fetched_task["title"].strip(),
                        fetched_task.get("notes", ""),
                        int(fetched_task["position"]),
                        TaskStatus(fetched_task.get("status", "unknown")),
                        [],
                    )

                    # If a task has a parent then it's definitely a subtask
                    # Subtask's parent might be incompleted so appending it
                    # to it must be deferred.
                    parent = fetched_task.get("parent", "")
                    if parent:
                        task_id_to_subtasks[parent].append(task)
                    else:
                        id_to_task_list[task_list_id].tasks.append(task)

            return fetch_tasks_request(task_list_id, completed), callback

        task_lists = self.task_lists().list(maxResults=100).execute().get("items", [])

        batched_request = self.new_batch_http_request()
        for task_list in task_lists:
            id = task_list["id"]
            id_to_task_list[id] = TaskList(id, task_list["title"], [])

            if not self.task_status or self.task_status == TaskStatus.PENDING:
                batched_request.add(*create_request_with_callback(id, False))
            if not self.task_status or self.task_status == TaskStatus.COMPLETED:
                batched_request.add(*create_request_with_callback(id, True))
        batched_request.execute()

        task_lists = list(id_to_task_list.values())
        task_lists.sort(key=lambda tl: tl.title)
        for task_list in task_lists:
            for task in task_list.tasks:
                task.subtasks = task_id_to_subtasks.get(task.id, [])
                task.subtasks.sort(key=lambda t: t.position)
            task_list.tasks.sort(key=lambda t: t.position)

        return task_lists

    # https://developers.google.com/tasks/quickstart/python#step_2_configure_the_sample
    def get_credentials(self) -> Credentials:
        """
        Read credentials from selected user configuration.

        This function will try to read existing token from
        $XDG_CACHE_HOME/gtasks-md directory for the selected user. If file with
        the token doesn't exist, it will try creating a new one after reading
        credentials from $XDG_DATA_HOME/gtasks-md. If there are no credentials
        the process will simply fail.
        """
        creds = None
        config_dir = f"{xdg_data_home()}/gtasks-md/{self.user}"
        credentials_file = f"{config_dir}/{CREDENTIALS_FILE}"
        cache_dir = f"{xdg_cache_home()}/gtasks-md/{self.user}"
        token_file = f"{cache_dir}/token.json"
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_file, "w+") as token:
                token.write(creds.to_json())

        return creds

    def save_credentials(self, credentials: str):
        """Save credentials to selected user config directory."""
        config_dir = f"{xdg_data_home()}/gtasks-md/{self.user}"

        with open(f"{config_dir}/{CREDENTIALS_FILE}", "w+") as dest_file:
            dest_file.write(credentials)

    def _get_service(self):
        if not self._service:
            self._service = build("tasks", "v1", credentials=self.get_credentials())
        return self._service


class ReconcileOp(Enum):
    INSERT = auto()
    DELETE = auto()
    UPDATE = auto()
