import unittest
from inspect import cleandoc

from app.parser import markdown_to_task_lists, task_lists_to_markdown
from app.tasks import Task, TaskList, TaskStatus


class TestMarkdownConversion(unittest.TestCase):
    def test_header_only(self):
        markdown = """
        # Google Tasks
        """

        self.assert_equal_after_parsing([], markdown)

    def test_task_list(self):
        task_list = create_task_list("Task List 1")
        markdown = """
        # Google Tasks

        ## Task List 1
        """

        self.assert_equal_after_parsing([task_list], markdown)

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

        1. [ ] Task 1

        2. [x] Task 2

        3. [ ] Task 3

           Some note.
        """

        self.assert_equal_after_parsing([task_list], markdown)

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

        1. [ ] Task 1

           Some note

           1. [ ] Subtask 1
           2. [ ] Subtask 2
           3. [ ] Subtask 3
        """

        self.assert_equal_after_parsing([task_list], markdown)

    def test_multiple_task_lists(self):
        task_lists = [
            create_task_list("Task List 1", create_task("Task 1")),
            create_task_list(
                "Task List 2", create_task("Task 2", status=TaskStatus.COMPLETED)
            ),
            create_task_list("Task List 3"),
        ]
        markdown = """
        # Google Tasks

        ## Task List 1

        1. [ ] Task 1

        ## Task List 2

        1. [x] Task 2

        ## Task List 3
        """

        self.assert_equal_after_parsing(task_lists, markdown)

    def test_special_characters_converge(self):
        task_list = create_task_list(
            "Task List 1",
            create_task("2*4 < 6 & _x_ `t`", note="Note with *stars*\nand [brackets]"),
        )

        markdown_1 = task_lists_to_markdown([task_list])
        task_lists_1 = markdown_to_task_lists(markdown_1)
        markdown_2 = task_lists_to_markdown(task_lists_1)
        task_lists_2 = markdown_to_task_lists(markdown_2)

        # mdformat escapes the lone "*" on the first write; after that both
        # the file and the parsed Task Lists must be stable. A failure here
        # most likely means an mdformat upgrade changed its escaping rules.
        task = task_lists_1[0].tasks[0]
        self.assertEqual("2\\*4 < 6 & _x_ `t`", task.title)
        self.assertEqual("Note with *stars*\nand [brackets]", task.note)
        self.assertEqual(markdown_1, markdown_2)
        self.assertEqual(task_lists_1, task_lists_2)

    def test_parse_task_without_checkbox(self):
        markdown = cleandoc(
            """
            # Google Tasks

            ## Task List 1

            1. Task 1
            2. [X] Task 2
            """
        )

        tasks = markdown_to_task_lists(markdown)[0].tasks
        self.assertEqual("Task 1", tasks[0].title)
        self.assertEqual(TaskStatus.UNKNOWN, tasks[0].status)
        self.assertEqual("Task 2", tasks[1].title)
        self.assertEqual(TaskStatus.COMPLETED, tasks[1].status)

    def test_parse_multiline_note(self):
        task_list = create_task_list(
            "Task List 1",
            create_task("Task 1", note="First paragraph.\n\nSecond\nparagraph."),
        )
        markdown = """
        # Google Tasks

        ## Task List 1

        1. [ ] Task 1

           First paragraph.

           Second
           paragraph.
        """

        self.assert_equal_after_parsing([task_list], markdown)

    def test_parse_lenient_formatting(self):
        task_list = create_task_list(
            "Task List 1",
            create_task(
                "Task 1",
                note="Some note",
                subtasks=[
                    create_task("Subtask 1"),
                    create_task("Subtask 2", status=TaskStatus.COMPLETED),
                ],
            ),
            create_task("Task 2", status=TaskStatus.COMPLETED),
        )
        # Hand-edited file: pandoc-style "1)" markers, wide markers and
        # varying indentation.
        markdown = """
        # Google Tasks

        ## Task List 1

        1)  [ ] Task 1

            Some note

            1.  [ ] Subtask 1
            2.  [x] Subtask 2

        2)  [x] Task 2
        """

        parsed_task_lists = markdown_to_task_lists(cleandoc(markdown.strip()))
        self.assertEqual([task_list], parsed_task_lists)

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

    def assert_equal_after_parsing(self, task_lists: list[TaskList], markdown: str):
        parsed_markdown = task_lists_to_markdown(task_lists)
        self.assert_equal_markdown(markdown, parsed_markdown)
        parsed_task_lists = markdown_to_task_lists(parsed_markdown)
        self.assertEqual(task_lists, parsed_task_lists)

    def assert_equal_markdown(self, text_1: str, text_2: str):
        self.assertEqual(cleandoc(text_1.strip()), cleandoc(text_2.strip()))


def create_task_list(name: str, *tasks) -> TaskList:
    return TaskList("", name, list(tasks))


def create_task(
    title: str,
    note: str = "",
    status: TaskStatus = TaskStatus.PENDING,
    subtasks: list[Task] | None = None,
) -> Task:
    return Task("", title, note, 0, status, subtasks or [])


if __name__ == "__main__":
    unittest.main()
