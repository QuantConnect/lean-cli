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

from pathlib import Path
from typing import Optional, List

from click import option, command

from lean.click import LeanCommand, PathParameter
from lean.constants import PROJECT_CONFIG_FILE_NAME
from lean.container import container


def _get_project_directories() -> List[Path]:
    directories_to_check = [container.lean_config_manager.get_cli_root_directory()]
    project_directories = []

    while len(directories_to_check) > 0:
        directory = directories_to_check.pop(0)

        config_file = directory / PROJECT_CONFIG_FILE_NAME
        if config_file.is_file():
            project_directories.append(directory)
        else:
            directories_to_check.extend(d for d in directory.iterdir() if d.is_dir())

    return project_directories


@command(cls=LeanCommand, requires_lean_config=True)
@option("--backtest", is_flag=True, default=False, help="Display the most recent backtest logs (default)")
@option("--live", is_flag=True, default=False, help="Display the most recent live logs")
@option("--optimization", is_flag=True, default=False, help="Display the most recent optimization logs")
@option("--project",
              type=PathParameter(exists=True, file_okay=False, dir_okay=True),
              help="The project to get the most recent logs from")
def logs(backtest: bool, live: bool, optimization: bool, project: Optional[Path]) -> None:
    """Display the most recent backtest/live/optimization logs."""
    if [backtest, live, optimization].count(True) > 1:
        raise RuntimeError("--backtest, --live and --optimization are mutually exclusive")

    if not backtest and not live and not optimization:
        backtest = True

    if backtest:
        mode = "backtest"
        mode_directory = "backtests"
    elif live:
        mode = "live"
        mode_directory = "live"
    elif optimization:
        mode = "optimization"
        mode_directory = "optimizations"

    if project is None:
        project_directories = _get_project_directories()
    else:
        project_directories = [project]

    most_recent_file = None
    most_recent_timestamp = None

    for project_directory in project_directories:
        target_directory = project_directory / mode_directory
        if not target_directory.is_dir():
            continue

        for session_directory in target_directory.iterdir():
            if not session_directory.is_dir():
                continue

            log_file = session_directory / "log.txt"
            if not log_file.is_file():
                continue

            log_file_timestamp = log_file.stat().st_mtime_ns
            if most_recent_file is None or log_file_timestamp > most_recent_timestamp:
                most_recent_file = log_file
                most_recent_timestamp = log_file_timestamp

    if most_recent_file is None:
        raise RuntimeError(f"No {mode} log file exists")

    print(most_recent_file.read_text(encoding="utf-8").strip())
