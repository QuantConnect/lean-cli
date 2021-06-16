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

import ctypes
import os
import platform
import site
import sys
import time
from pathlib import Path


# Docker's pywin32 dependency on Windows is a common source of issues
# In a lot of cases you'd have to manually run pywin32's post-install script as admin after pip installing the library
# This is a hassle, so the CLI attempts to automate this step when it's necessary
# Additionally, we can also fix the issues for some users by updating os.environ["PATH"]
# If this works we use this fix instead as it removes the need to request admin permissions
# This code must run before the Docker package is imported anywhere in the code

def _is_win32_available() -> bool:
    try:
        # Try the win32 APIs used by https://github.com/docker/docker-py/blob/master/docker/transport/npipesocket.py
        import win32file
        import win32pipe
        return True
    except:
        return False


def _ensure_win32_available() -> None:
    if _is_win32_available():
        return

    possible_paths = sys.path + [sys.prefix] + site.getsitepackages() + [site.getusersitepackages()]
    possible_paths = [Path(p) for p in possible_paths]
    possible_directories = set(p for p in possible_paths if p.is_dir())

    for directory in possible_directories:
        target_directory = directory / "pywin32_system32"
        if not target_directory.is_dir():
            continue

        os.environ["PATH"] += ";" + str(target_directory)

        if _is_win32_available():
            return

    for directory in possible_directories:
        target_file = directory / "Scripts" / "pywin32_postinstall.py"
        if not target_file.is_file():
            continue

        print(f"Running pywin32's post-install script at {target_file}")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{target_file}" -install', None, 1)

        # ShellExecuteW returns immediately after the UAC dialog, we wait a second to give the script some time to run
        time.sleep(1)

        if _is_win32_available():
            return

    print("pywin32 has not been installed completely, which may lead to errors")
    print("You can fix this issue by running pywin32's post-install script")
    print(f"Run the following command in an elevated terminal from your Python environment's Scripts directory:")
    print("python pywin32_postinstall.py -install")


if platform.system() == "Windows":
    _ensure_win32_available()

import traceback
from io import StringIO

import click
import requests
from pydantic import ValidationError

from lean.commands import lean
from lean.container import container
from lean.models.errors import MoreInfoError


def main() -> None:
    """This function is the entrypoint when running a Lean command in a terminal."""
    try:
        lean.main(standalone_mode=False)
        container.temp_manager().delete_temporary_directories()
    except Exception as exception:
        logger = container.logger()
        logger.debug(traceback.format_exc().strip())

        if isinstance(exception, ValidationError) and hasattr(exception, "input_value"):
            logger.debug("Value that failed validation:")
            logger.debug(exception.input_value)
            logger.error(f"Error: {exception}")
        elif isinstance(exception, MoreInfoError):
            logger.error(f"Error: {exception}")
            logger.error(f"Visit {exception.link} for more information")
        elif isinstance(exception, click.UsageError):
            io = StringIO()
            exception.show(file=io)

            exception_str = io.getvalue().strip()
            exception_str = exception_str.replace("Try 'lean", "\nTry 'lean")
            exception_str = exception_str.replace("for help.",
                                                  "for help or go to the following url for a list of common errors:\nhttps://www.lean.io/docs/lean-cli/user-guides/troubleshooting")

            logger.info(exception_str)
        elif isinstance(exception, click.Abort):
            logger.info("Aborted!")
        elif isinstance(exception, requests.exceptions.ConnectionError):
            logger.error(f"Error: {exception}")
            logger.error("It looks like you don't have an internet connection, please check your system settings")
        else:
            logger.error(f"Error: {exception}")

        container.temp_manager().delete_temporary_directories()
        sys.exit(1)
