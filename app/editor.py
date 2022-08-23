import os
import subprocess
import tempfile

from xdg import xdg_cache_home


class Editor:
    """
    Handles all editor-related functionality.
    """

    def __init__(self, editor: str = ""):
        self.format = format

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
        self._backup(text)

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

    def _backup(self, text: str):
        cacheDir = f"{xdg_cache_home()}/gtasks-md"

        with open(f"{cacheDir}/marker", "r+") as marker_file:
            marker = marker_file.read()
            file_no = ((int(marker) if marker else 0) + 1) % 10
            marker_file.seek(0)
            marker_file.write(str(file_no))
            marker_file.truncate()

            with open(f"{cacheDir}/{file_no}.bak.md", "w") as backup_file:
                backup_file.write(text)
