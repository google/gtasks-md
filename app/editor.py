import os
import subprocess
import tempfile

import pandoc


class Editor:
    def __init__(self, editor=""):
        if editor:
            self.editor = editor
        elif os.environ["EDITOR"]:
            self.editor = os.environ["EDITOR"]
        elif os.environ["VISUAL"]:
            self.editor = os.environ["VISUAL"]
        else:
            self.editor = "vim"

    def edit(self, txt):
        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            tmp.write(str.encode(txt))
            tmp.flush()
            if subprocess.call([self.editor, tmp.name]) != 0:
                exit(1)
            return pandoc.read(file=tmp.name)
