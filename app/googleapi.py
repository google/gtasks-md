import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from enum import Enum, auto

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from xdg import xdg_cache_home, xdg_config_home

from .tasks import Task, TaskList, TaskStatus

CREDENTIALS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/tasks"]
TOKEN_FILE = "token.json"


# https://googleapis.github.io/google-api-python-client/docs/dyn/tasks_v1.html
class GoogleApiService:
    def __init__(self, user):
        self.user = user
        self._service = None

    def tasks(self):
        if not self._service:
            self._service = build("tasks", "v1", credentials=self.get_credentials())
        return self._service.tasks()

    def task_lists(self):
        if not self._service:
            self._service = build("tasks", "v1", credentials=self.get_credentials())
        return self._service.tasklists()

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
                task_list_to_op[task_list.title] = (ReconcileOp.REMOVE, task_list)

            for task_list in new_task_lists:
                if task_list.title in task_list_to_op:
                    task_list_to_op[task_list.title] = (
                        ReconcileOp.UPDATE,
                        task_list_to_op[task_list.title][1],
                        task_list,
                    )
                else:
                    task_list_to_op[task_list.title] = (ReconcileOp.ADD, task_list)

            return list(task_list_to_op.values())

        async def apply_task_list_op(op):
            match op:
                case (ReconcileOp.REMOVE, task_list):
                    self.task_lists().delete(tasklist=task_list.id).execute()
                    logging.info(f"Removed Task List {task_list.title}")

                case (ReconcileOp.ADD, task_list):
                    response = (
                        self.task_lists().insert(body=task_list.toRequest()).execute()
                    )
                    task_list_id = response["id"]
                    new_tasks = apply_task_ops(
                        gen_task_ops([], task_list.tasks),
                        task_list.tasks,
                        task_list_id,
                    )
                    fix_task_order(task_list_id, new_tasks)
                    logging.info(f"Added Task List {task_list.title}")

                case (ReconcileOp.UPDATE, old_task_list, new_task_list):
                    if old_task_list != new_task_list:
                        new_tasks = apply_task_ops(
                            gen_task_ops(old_task_list.tasks, new_task_list.tasks),
                            new_task_list.tasks,
                            old_task_list.id,
                        )
                        fix_task_order(old_task_list.id, new_tasks)
                        logging.info(f"Updated Task List {old_task_list.title}")

        def gen_task_ops(old_tasks: list[Task], new_tasks: list[Task]):
            task_to_op = {}
            for task in old_tasks:
                task_to_op[task.title] = (ReconcileOp.REMOVE, task)

            for i, task in enumerate(new_tasks):
                if task.title in task_to_op:
                    task_to_op[task.title] = (
                        ReconcileOp.UPDATE,
                        task_to_op[task.title][1],
                        task,
                        i,
                    )
                else:
                    task_to_op[task.title] = (ReconcileOp.ADD, task, i)

            return list(task_to_op.values())

        def apply_task_ops(ops, new_tasks, task_list_id):
            for op in ops:
                match op:
                    case (ReconcileOp.REMOVE, task):
                        self.tasks().delete(
                            tasklist=task_list_id, task=task.id
                        ).execute()
                        logging.info(f"Removed Task {task.title}")

                    case (ReconcileOp.ADD, task, idx):
                        response = (
                            self.tasks()
                            .insert(tasklist=task_list_id, body=task.toRequest())
                            .execute()
                        )
                        task_id = response["id"]
                        new_tasks[idx].id = task_id  # Needed for fix_task_order

                        new_subtasks = apply_task_ops(
                            gen_task_ops([], task.subtasks),
                            task.subtasks,
                            task_list_id,
                        )
                        fix_task_order(
                            task_list_id,
                            new_subtasks,
                            task_id,
                        )
                        new_tasks[idx].subtasks = new_subtasks
                        logging.info(f"Added Task {task.title}")

                    case (ReconcileOp.UPDATE, old_task, new_task, idx):
                        new_tasks[idx].id = old_task.id  # Needed for fix_task_order

                        if old_task != new_task:
                            response = (
                                self.tasks()
                                .patch(
                                    tasklist=task_list_id,
                                    task=old_task.id,
                                    body=new_task.toRequest(),
                                )
                                .execute()
                            )

                            new_subtasks = apply_task_ops(
                                gen_task_ops(old_task.subtasks, new_task.subtasks),
                                new_task.subtasks,
                                task_list_id,
                            )
                            fix_task_order(
                                task_list_id,
                                new_subtasks,
                                old_task.id,
                            )
                            new_tasks[idx].subtasks = new_subtasks

                            logging.info(f"Updated Task {old_task.title}")

            return new_tasks

        def fix_task_order(task_list_id, new_tasks, parent=""):
            for i, task in enumerate(new_tasks):
                if not task.completed():
                    previous_task = new_tasks[i - 1] if i > 0 else None
                    previous_task_id = previous_task.id if previous_task else ""

                    self.tasks().move(
                        tasklist=task_list_id,
                        task=task.id,
                        parent=parent,
                        previous=previous_task_id,
                    ).execute()

                    previous_task_title = (
                        previous_task.title if previous_task else "NONE"
                    )
                    logging.info(
                        f"Moved task {task.title} after {previous_task_title} (parent: {parent})"
                    )

        async_tasks = []
        for op in gen_tasklist_ops():
            async_tasks.append(asyncio.create_task(apply_task_list_op(op)))
        await asyncio.gather(*async_tasks)

    async def fetch_task_lists(self) -> list[TaskList]:
        """
        Fetches all tasks from the server.

        At first the function fetches up to 100 task lists. Then it fetches all
        tasks for these task lists that are either completed at most 30 days ago
        or are still pending completion.
        """

        async def process_task_list(id, title):
            async def fetch_tasks(completed):
                one_month_ago = (
                    (datetime.now(timezone.utc) - timedelta(days=30))
                    .astimezone()
                    .isoformat()
                    if completed
                    else ""
                )

                items = []
                next_page_token = ""
                while True:
                    result = (
                        self.tasks()
                        .list(
                            completedMin=one_month_ago,
                            pageToken=next_page_token,
                            showCompleted=completed,
                            showHidden=completed,
                            tasklist=id,
                        )
                        .execute()
                    )
                    items = items + result.get("items", [])
                    next_page_token = result.get("nextPageToken", "")
                    if not next_page_token:
                        break

                return items

            incompleted, completed = await asyncio.gather(
                asyncio.create_task(fetch_tasks(False)),
                asyncio.create_task(fetch_tasks(True)),
            )

            tasks = {}
            subtasks = []
            for task in incompleted + completed:
                parsed_task = Task(
                    task["title"].strip(),
                    task["id"],
                    task.get("notes", ""),
                    int(task["position"]),
                    TaskStatus(task.get("status", "unknown")),
                    [],
                )

                # If a task has a parent then it's definitely a subtask
                parent = task.get("parent", "")
                if not parent:
                    tasks[parsed_task.id] = parsed_task
                else:
                    subtasks.append((parent, parsed_task))

            for (parent, task) in subtasks:
                tasks[parent].subtasks.append(task)

            # Sort tasks and subtasks by position
            out = list(tasks.values())
            out.sort(key=lambda t: t.position)
            for task in out:
                task.subtasks.sort(key=lambda st: st.position)

            return TaskList(title, id, out)

        result = self.task_lists().list(maxResults=100).execute()

        async_tasks = []
        for task_list in result.get("items", []):
            async_task = asyncio.create_task(
                process_task_list(task_list["id"], task_list["title"])
            )
            async_tasks.append(async_task)

        return await asyncio.gather(*async_tasks)

    # https://developers.google.com/tasks/quickstart/python#step_2_configure_the_sample
    def get_credentials(self) -> Credentials:
        """
        Read credentials from selected user configuration.

        This function will try to read existing token from $XDG_CACHE_HOME/gtasks-md
        directory for the selected user. If file with the token doesn't exist, it
        will try creating a new one after reading credentials from
        $XDG_CONFIG_HOME/gtasks-md. If there are no credentials the process will
        simply fail.
        """
        creds = None
        config_dir = f"{xdg_config_home()}/gtasks-md/{self.user}"
        credentials_file = f"{config_dir}/{CREDENTIALS_FILE}"
        cache_dir = f"{xdg_cache_home()}/gtasks-md/{self.user}"
        token_file = f"{cache_dir}/{TOKEN_FILE}"
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
        config_dir = f"{xdg_config_home()}/gtasks-md/{self.user}"

        with open(f"{config_dir}/{CREDENTIALS_FILE}", "w+") as dest_file:
            dest_file.write(credentials)


class ReconcileOp(Enum):
    ADD = auto()
    REMOVE = auto()
    UPDATE = auto()
