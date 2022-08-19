# Design (draft)

I want to have a tool that allows me to keep my Google Tasks as a markdown file.
The first version (PoC) should allow me to view this file. The second version
should allow me to edit it. And later will deal with other important issues
(like handling synchronisation errors). A Neovim plugin may be created as a
byproduct.

## Document language

Markdown flavor should be commonmark (subset, to be exact). The file will look
something like that:

``` markdown
# TODO

## Tasklist 1

1.  [ ] Task 1
    1.  [ ] Subtask 1
    2.  [x] Subtask 2
2.  [x] Task 2
    1.  [x] Subtask 1

## Tasklist 2

1.  [ ] Task 1

    Task 1 description.

    1.  [ ] Subtask 1

        Subtask 1 description.

    2.  [ ] Subtask 2

        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris mauris
        mi, luctus non vulputate quis, gravida eu dolor. Pellentesque habitant
        morbi tristique senectus et netus et malesuada fames ac turpis egestas.
```

Parser may use [tree-sitter for markdown]. TBD if that would be helpful. All
tasks are ordered. Any unordered sublist should be treated as description. There
is no support for handling links (`[x](y)`) or images (`![x](y)`). There is no
support for attachments. Everything inside the ordered lists (up to single-level
nesting) should be treated as plaintext.

## Programming language

The tool should be developed with either python or go. Python has the following
advantages:

-   There is official support in Google documentation
-   There is official library with bindings for python:
    https://github.com/tree-sitter/py-tree-sitter

Goland shares the first advantage. The tree-sitter binding library is developed
by a third-party: https://github.com/smacker/go-tree-sitter and looks more
complicated.

Despite my fondness of Go, I might roll with Python in this project. What's the
worst that could happen.

  [tree-sitter for markdown]: https://github.com/MDeiml/tree-sitter-markdown
