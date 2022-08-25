import os
import subprocess
import tempfile


class Editor:
    """
    Handles all editor-related functionality.
    """

    def __init__(self, editor):
        if editor:
            self.editor = editor
        elif "VISUAL" in os.environ:
            self.editor = os.environ["VISUAL"]
        elif "EDITOR" in os.environ:
            self.editor = os.environ["EDITOR"]
        else:
            self.editor = "vim"

    def edit(self, text: str) -> str:
        """
        Edit given markdown text.

        A backup of the input will be stored in the $XDG_CACHE_HOME/gtasks-md
        directory. Next, the text will be stored in a temporary file that will
        be edited with provided editor. In case the editor is missing, the
        program will try the following options: $VISUAL, $EDITOR and "vim".
        """

        tmp_file = ""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp.write(str.encode(text))
            tmp.flush()
            if subprocess.call([self.editor, tmp.name]) != 0:
                exit(1)
            tmp_file = tmp.name

        out = ""
        with open(tmp_file, "r") as output:
            out = output.read()

        os.remove(tmp_file)
        return out
