import unittest
from inspect import cleandoc

from .pandoc import markdown_to_task_lists, task_lists_to_markdown
from .tasks import Task, TaskList, TaskStatus


class TestPandocConversion(unittest.TestCase):
    def test_header_only(self):
        markdown = """
        # Google Tasks
        """

        self.assertEqualAfterParsing([], markdown)

    def test_task_list(self):
        task_list = create_task_list("Task List 1")
        markdown = """
        # Google Tasks

        ## Task List 1
        """

        self.assertEqualAfterParsing([task_list], markdown)

    def test_task_list_with_tasks(self):
        task_list = create_task_list(
            "Task List 1",
            create_task("Task 1"),
            create_task("Task 2", status=TaskStatus.COMPLETED),
            create_task("Task 3", "Some note."),
        )
        markdown = """
        # Google Tasks

        ## Task List 1

        1.  [ ] Task 1

        2.  [x] Task 2

        3.  [ ] Task 3

            Some note.
        """

        self.assertEqualAfterParsing([task_list], markdown)

    def test_task_list_with_task_with_subtasks(self):
        task_list = create_task_list(
            "Task List 1",
            create_task(
                "Task 1",
                note="Some note",
                subtasks=[
                    create_task("Subtask 1"),
                    create_task("Subtask 2"),
                    create_task("Subtask 3"),
                ],
            ),
        )
        markdown = """
        # Google Tasks

        ## Task List 1

        1.  [ ] Task 1

            Some note

            1.  [ ] Subtask 1
            2.  [ ] Subtask 2
            3.  [ ] Subtask 3
        """

        self.assertEqualAfterParsing([task_list], markdown)

    def test_fail_to_parse_invalid_header(self):
        markdown = """
        # Google Tasks

        ## Task List 1

        ### Task 1
        """

        self.assertRaises(SyntaxError, markdown_to_task_lists, markdown)

    def test_fail_to_parse_unexpected_paragraph(self):
        markdown = """
        # Google Tasks

        ## Task List 1

        1.  [ ] Task 1
        2.  [x] Task 2

        Some paragraph.
        """

        self.assertRaises(SyntaxError, markdown_to_task_lists, markdown)

    def assertEqualAfterParsing(self, task_lists: list[TaskList], markdown: str):
        parsed_markdown = task_lists_to_markdown(task_lists)
        self.assertEqualMarkdown(markdown, parsed_markdown)
        parsed_task_lists = markdown_to_task_lists(parsed_markdown)
        self.assertEqual(task_lists, parsed_task_lists)

    def assertEqualMarkdown(self, text_1: str, text_2: str):
        self.assertEqual(cleandoc(text_1.strip()), cleandoc(text_2.strip()))


def create_task_list(name: str, *tasks) -> TaskList:
    return TaskList("", name, list(tasks))


def create_task(
    title: str,
    note: str = "",
    status: TaskStatus = TaskStatus.PENDING,
    subtasks: list[Task] = [],
) -> Task:
    return Task("", title, note, 0, status, subtasks)


if __name__ == "__main__":
    unittest.main()
