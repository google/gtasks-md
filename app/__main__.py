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
import argparse
import asyncio
import datetime
import logging
import os
from datetime import timedelta

from xdg import xdg_cache_home, xdg_data_home

from .backup import Backup
from .editor import Editor
from .googleapi import GoogleApiService
from .pandoc import markdown_to_task_lists, task_lists_to_markdown


def main():
    args = parse_args()

    config_dir = f"{xdg_data_home()}/gtasks-md/{args.user}/"
    os.makedirs(os.path.dirname(config_dir), exist_ok=True)
    cache_dir = f"{xdg_cache_home()}/gtasks-md/{args.user}/"
    os.makedirs(os.path.dirname(cache_dir), exist_ok=True)

    logging.basicConfig(
        filename=f"{xdg_cache_home()}/gtasks-md/log.txt",
        format="%(asctime)s %(levelname)-8s %(message)s",
        encoding="utf-8",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    service = GoogleApiService(
        args.user, args.completed_after, args.completed_before, args.status
    )
    match args.subcommand:
        case "auth":
            auth(service, args.credentials_file)
        case "edit":
            editor = Editor(args.editor)
            backup = Backup(args.user)
            edit(service, editor, backup)
        case "reconcile":
            backup = Backup(args.user)
            reconcile(service, args.file_path, backup)
        case "rollback":
            backup = Backup(args.user)
            rollback(service, backup)
        case "view":
            view(service)
        case None:
            print("Please run one of the subcommands.")


def parse_args():
    def parse_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%d").astimezone()

    # https://stackoverflow.com/a/49977713
    parser = argparse.ArgumentParser(description="Google Tasks declarative management.")
    parser.add_argument(
        "--completed-after",
        dest="completed_after",
        default=(datetime.datetime.now() - timedelta(days=7)).astimezone(),
        help="Only show tasks completed after given date. The date must be in format YYYY-MM-DD. Defaults to one week ago.",
        type=parse_date,
    )
    parser.add_argument(
        "--completed-before",
        dest="completed_before",
        default=None,
        help="Only show tasks completed before given date. The date must be in format YYYY-MM-DD.",
        type=lambda d: parse_date(d) if d else None,
    )
    parser.add_argument(
        "--status",
        dest="status",
        default="",
        help="Task status. One of: needsAction, completed.",
        type=str.lower,
    )
    parser.add_argument(
        "--user",
        dest="user",
        default="default",
        help="Account for which the credentials are sourced. Should match desired Google account.",
        type=str,
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    auth = subparsers.add_parser("auth", help="Authorize.")
    auth.add_argument(
        "credentials_file",
        help="Location of credential file.",
        type=str,
    )

    edit_parser = subparsers.add_parser("edit", help="Edit Google Tasks.")
    edit_parser.add_argument(
        "--editor",
        dest="editor",
        default="",
        help="Editor to be used for editing tasks. Defaults to $EDITOR and then $VISUAL and then vim.",
        type=str,
    )

    reconcile_parser = subparsers.add_parser(
        "reconcile", help="Patch Task Lists with an offline source."
    )
    reconcile_parser.add_argument(
        "file_path",
        help="Location of the source file.",
        type=str,
    )

    subparsers.add_parser("rollback", help="Rollback last change.")
    subparsers.add_parser("view", help="View Google Tasks.")

    return parser.parse_args()


def auth(service: GoogleApiService, file: str):
    with open(file, "r") as src_file:
        service.save_credentials(src_file.read())


def view(service: GoogleApiService):
    _, text = fetch_task_lists(service)
    print(text)


def edit(service: GoogleApiService, editor: Editor, backup: Backup):
    old_task_lists, old_text = fetch_task_lists(service)
    new_text = editor.edit(old_text)
    new_task_lists = markdown_to_task_lists(new_text)
    backup.write_backup(old_text)
    asyncio.run(service.reconcile(old_task_lists, new_task_lists))


def reconcile(service: GoogleApiService, file_path: str, backup: Backup | None = None):
    old_task_lists, old_text = fetch_task_lists(service)

    with open(file_path, "r") as source:
        new_text = source.read()
        new_task_lists = markdown_to_task_lists(new_text)
        if backup:
            backup.write_backup(old_text)
        asyncio.run(service.reconcile(old_task_lists, new_task_lists))


def rollback(service: GoogleApiService, backup: Backup):
    backup_file = backup.discard_backup()
    if backup_file:
        reconcile(service, backup_file, None)
    else:
        print("No backup found")


def fetch_task_lists(service: GoogleApiService):
    task_lists = service.fetch_task_lists()
    return task_lists, task_lists_to_markdown(task_lists)


if __name__ == "__main__":
    main()
