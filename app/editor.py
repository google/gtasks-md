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
