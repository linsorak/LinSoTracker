"""Launcher for the standalone updater binary shipped next to the application.

The updater is self-sufficient: it downloads the manifest itself, compares
versions, fetches and extracts the archive behind its own tkinter progress
window, then relaunches the tracker. The application only has to spawn it with
the right arguments and get out of the way, because the archive overwrites the
executable that is still running.

Command line contract of updater.exe (recovered from the shipped binary):

    --current_version   Current version of the tracker
    --destination_path  Where to extract the patch
    --file_to_execute   File to execute after patch
    --url_json          URL of the reference json

It resolves the platform itself (win / linux / macARM64 / macIntel) and reads
"lastest_version" and "url_base" from the manifest.
"""

import os
import subprocess
import sys

from Tools.CoreService import UPDATE_CONFIGURATION_URL


class UpdateError(Exception):
    """Raised when the updater binary cannot be found or started."""


class AutoUpdater:
    def __init__(self, core_service):
        self.core_service = core_service

    def updater_filename(self):
        return "updater.exe" if self.core_service.detect_os() == "win" else "updater"

    def get_updater_path(self):
        return os.path.join(self.core_service.app_path, self.updater_filename())

    def is_available(self):
        return os.path.isfile(self.get_updater_path())

    def get_application_path(self):
        """The binary the updater has to relaunch once the patch is applied."""
        if getattr(sys, "frozen", False):
            return os.path.abspath(sys.executable)
        name = f"{self.core_service.app_name}.exe" \
            if self.core_service.detect_os() == "win" else self.core_service.app_name
        return os.path.join(self.core_service.app_path, name)

    def build_command(self):
        return [
            self.get_updater_path(),
            "--current_version", self.core_service.get_version(),
            "--destination_path", self.core_service.app_path,
            "--file_to_execute", self.get_application_path(),
            "--url_json", UPDATE_CONFIGURATION_URL,
        ]

    def launch(self):
        """Spawn the updater detached. The caller must exit immediately after."""
        updater_path = self.get_updater_path()
        if not os.path.isfile(updater_path):
            raise UpdateError(
                f"{self.updater_filename()} is missing from {self.core_service.app_path}.\n\n"
                "Download the latest release from linsotracker.com.")

        command = self.build_command()
        try:
            if self.core_service.detect_os() == "win":
                creation_flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                subprocess.Popen(command, close_fds=True, creationflags=creation_flags,
                                 cwd=self.core_service.app_path)
            else:
                os.chmod(updater_path, 0o755)
                subprocess.Popen(command, close_fds=True, start_new_session=True,
                                 cwd=self.core_service.app_path)
        except OSError as exc:
            raise UpdateError(f"Cannot start the updater: {exc}")
        return command
