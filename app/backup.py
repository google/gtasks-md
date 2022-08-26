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
from pathlib import Path

from xdg import xdg_cache_home


class Backup:
    """
    Handles all backup-related functionality.
    """

    def __init__(self, user):
        self.user = user

    def write_backup(self, text: str):
        cache_dir = f"{xdg_cache_home()}/gtasks-md/{self.user}"
        marker_file_path = Path(f"{cache_dir}/marker")

        marker_file_path.touch()
        with marker_file_path.open("r+") as marker_file:
            marker = marker_file.read()
            file_no = (int(marker) + 1 if marker else 0) % 10
            marker_file.seek(0)
            marker_file.write(str(file_no))
            marker_file.truncate()

            with open(f"{cache_dir}/{file_no}.bak.md", "w") as backup_file:
                backup_file.write(text)

    def discard_backup(self):
        cache_dir = f"{xdg_cache_home()}/gtasks-md/{self.user}"
        marker_file_path = Path(f"{cache_dir}/marker")

        if not marker_file_path.is_file():
            return None

        with marker_file_path.open("r+") as marker_file:
            marker = marker_file.read()
            file_no = ((int(marker) if marker else 0)) % 10
            marker_file.seek(0)
            marker_file.write(str(file_no - 1))
            marker_file.truncate()

            return f"{cache_dir}/{file_no}.bak.md"
