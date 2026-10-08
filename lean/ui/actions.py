# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shlex import quote
from typing import Callable, List, Optional

from lean.ui.projects import UIProject
from lean.ui.results import list_local_backtests


@dataclass(frozen=True)
class ProjectAction:
    """Something to do with a project from the UI, usually running a Lean CLI command."""

    key: str
    label: str
    build_args: Optional[Callable[[UIProject], List[str]]] = None
    needs_local: bool = False
    needs_cloud_project: bool = False
    needs_login: bool = False
    refreshes_projects: bool = False
    opens_results: bool = False
    live: Optional[str] = None
    """'local' or 'cloud' for backtests, which open their results right away instead of asking to confirm."""

    def unavailable_reason(self, project: UIProject, logged_in: bool) -> Optional[str]:
        """Returns why the action cannot run on the project, or None if it can."""
        if self.opens_results:
            if list_local_backtests(project.path) or (project.is_cloud and logged_in):
                return None
            return "run `lean login` first" if project.is_cloud else "no backtests yet"
        if self.needs_local and not project.is_local:
            return "pull it first"
        if self.needs_login and not logged_in:
            return "run `lean login` first"
        if self.needs_cloud_project and not project.is_cloud:
            return "push it first"
        return None


def _cloud_name(project: UIProject) -> str:
    """Cloud commands accept the project id, which avoids local and cloud names differing."""
    return str(project.cloud_id) if project.is_cloud else project.name


ACTIONS = [
    ProjectAction("b", "Backtest locally", lambda p: ["backtest", p.name], needs_local=True, live="local"),
    ProjectAction("c", "Backtest in the cloud",
                  lambda p: ["cloud", "backtest", p.name, "--push"] if p.is_local
                  else ["cloud", "backtest", _cloud_name(p)],
                  needs_login=True, refreshes_projects=True, live="cloud"),
    ProjectAction("v", "View backtest results", opens_results=True),
    ProjectAction("p", "Push to the cloud", lambda p: ["cloud", "push", "--project", p.name],
                  needs_local=True, needs_login=True, refreshes_projects=True),
    ProjectAction("u", "Pull from the cloud", lambda p: ["cloud", "pull", "--project", _cloud_name(p)],
                  needs_cloud_project=True, needs_login=True, refreshes_projects=True),
    ProjectAction("s", "Cloud live status", lambda p: ["cloud", "status", _cloud_name(p)],
                  needs_cloud_project=True, needs_login=True),
]

# `lean cloud backtest` prints the url of the backtest it creates, which holds the project and backtest ids
CLOUD_BACKTEST_URL = re.compile(r"quantconnect\.com/project/(\d+)/([0-9a-f]{32})")


def format_command(args: List[str]) -> str:
    """Formats arguments as the `lean` command a user would type."""
    return " ".join(["lean"] + [quote(a) for a in args])


class CommandProcess:
    """Runs a Lean CLI command as a child process, so its console output cannot draw over the UI."""

    def __init__(self, args: List[str], cwd: Path) -> None:
        self.args = args
        self._cwd = cwd
        self._process: Optional[subprocess.Popen] = None
        self._stop_requested = False

    def run(self, on_line: Callable[[str], None]) -> int:
        """Runs the command to completion, passing each line of output to on_line. Blocks the calling thread.

        :return: the exit code of the command
        """
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", COLUMNS="120")
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0

        self._process = subprocess.Popen([sys.executable, "-m", "lean"] + self.args,
                                         cwd=self._cwd,
                                         env=env,
                                         stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT,
                                         encoding="utf-8",
                                         errors="replace",
                                         creationflags=creation_flags)

        for line in self._process.stdout:
            on_line(line.rstrip("\r\n"))

        return self._process.wait()

    def stop(self) -> None:
        """Asks the command to stop the way Ctrl+C would, so it can clean up its Docker containers.

        Calling this again while the command is still running kills it.
        """
        if self._process is None or self._process.poll() is not None:
            return

        if self._stop_requested:
            self._process.kill()
            return
        self._stop_requested = True

        import signal
        if sys.platform == "win32":
            self._process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            self._process.send_signal(signal.SIGINT)
