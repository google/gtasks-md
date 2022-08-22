import argparse

import pandoc

from .editor import Editor
from .googleapi import GoogleApiService
from .pandoc import pandoc_to_tasklists, tasklists_to_pandoc


def main():
    args = parse_args()

    match args.subcommand:
        case "edit":
            edit(Editor(args.editor))
        case "view":
            view()
        case None:
            print("Please run one of the subcommands.")


def view():
    svc = GoogleApiService()
    _, text = fetch_tasklists(svc)
    print(text)


def parse_args():
    # https://stackoverflow.com/a/49977713
    parser = argparse.ArgumentParser(description="Google Tasks declarative management.")
    subparsers = parser.add_subparsers(dest="subcommand")

    subparsers.add_parser("view", help="View Google Tasks.")

    editParser = subparsers.add_parser("edit", help="Edit Google Tasks.")
    editParser.add_argument(
        "--editor",
        dest="editor",
        default="",
        help="Editor to be used for editing tasks. Defaults to $EDITOR and then $VISUAL and then vim.",
    )

    return parser.parse_args()


def edit(editor):
    svc = GoogleApiService()
    oldTaskLists, text = fetch_tasklists(svc)
    newTaskLists = pandoc_to_tasklists(editor.edit(text))
    svc.reconcile(oldTaskLists, newTaskLists)


def fetch_tasklists(service):
    taskLists = service.get_tasklists()
    doc = tasklists_to_pandoc(taskLists)
    return taskLists, pandoc.write(doc)


if __name__ == "__main__":
    main()
