# Copyright 2026 Google LLC
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
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gtasks_md.backup import Backup


class TestBackup(unittest.TestCase):
    def setUp(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)

        env_patcher = mock.patch.dict("os.environ", {"XDG_CACHE_HOME": tmp_dir.name})
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        self.cache_dir = Path(tmp_dir.name) / "gtasks-md" / "test"
        self.cache_dir.mkdir(parents=True)
        self.backup = Backup("test")

    def test_discard_without_marker(self):
        self.assertIsNone(self.backup.discard_backup())

    def test_write_then_discard(self):
        self.backup.write_backup("some text")

        backup_file = self.backup.discard_backup()

        self.assertIsNotNone(backup_file)
        self.assertEqual("some text", Path(backup_file).read_text(encoding="utf-8"))

    def test_discard_more_times_than_backups_written(self):
        self.backup.write_backup("first")
        self.backup.write_backup("second")

        first = self.backup.discard_backup()
        second = self.backup.discard_backup()

        self.assertEqual("second", Path(first).read_text(encoding="utf-8"))
        self.assertEqual("first", Path(second).read_text(encoding="utf-8"))
        self.assertIsNone(self.backup.discard_backup())

    def test_marker_wraps_around(self):
        self.backup.write_backup("some text")
        self.backup.discard_backup()

        marker = (self.cache_dir / "marker").read_text(encoding="utf-8")
        self.assertEqual("9", marker)

        # A subsequent backup reuses slot 0, as if nothing was discarded.
        self.backup.write_backup("new text")
        backup_file = self.backup.discard_backup()
        self.assertEqual("0.bak.md", Path(backup_file).name)
        self.assertEqual("new text", Path(backup_file).read_text(encoding="utf-8"))
