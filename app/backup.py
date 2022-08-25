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
            file_no = ((int(marker) if marker else 0) + 1) % 10
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
            file_no = ((int(marker) if marker else 0) - 1) % 10
            marker_file.seek(0)
            marker_file.write(str(file_no))
            marker_file.truncate()

            return f"{cache_dir}/{file_no}.bak.md"
