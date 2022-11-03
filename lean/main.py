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

from platform import system

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

    from site import getsitepackages, getusersitepackages
    from sys import executable, path, exit, prefix
    from os import environ
    from pathlib import Path

    possible_paths = path + [prefix] + getsitepackages() + [getusersitepackages()]
    possible_paths = [Path(p) for p in possible_paths]
    possible_directories = set(p for p in possible_paths if p.is_dir())

    for directory in possible_directories:
        target_directory = directory / "pywin32_system32"
        if not target_directory.is_dir():
            continue

        environ["PATH"] += ";" + str(target_directory)

        if _is_win32_available():
            return

    for directory in possible_directories:
        target_file = directory / "Scripts" / "pywin32_postinstall.py"
        if not target_file.is_file():
            continue

        from ctypes import windll
        print(f"Running pywin32's post-install script at {target_file}")
        windll.shell32.ShellExecuteW(None, "runas", executable, f'"{target_file}" -install', None, 1)

        # ShellExecuteW returns immediately after the UAC dialog, we wait a second to give the script some time to run
        from time import sleep
        sleep(1)

        if _is_win32_available():
            return

    if any("AppData\\Local\\Packages\\PythonSoftwareFoundation.Python" in p for p in path):
        print("It looks like you're using the Python distribution from the Microsoft Store")
        print("This distribution is not supported by the CLI, we recommend using the Anaconda distribution instead")
        print(
            "See https://www.lean.io/docs/v2/lean-cli/installation/installing-pip#02-Install-on-Windows for more information")
        exit(1)

    print("pywin32 has not been installed completely, which may lead to errors")
    print("You can fix this issue by running pywin32's post-install script")
    print(f"Run the following command in an elevated terminal from your Python environment's Scripts directory:")
    print("python pywin32_postinstall.py -install")

if system() == "Windows":
    _ensure_win32_available()

from lean.commands import lean
from lean.container import container


def main() -> None:
    """This function is the entrypoint when running a Lean command in a terminal."""
    try:
        lean.main(standalone_mode=False)

        temp_manager = container.temp_manager
        if temp_manager.delete_temporary_directories_when_done:
            temp_manager.delete_temporary_directories()
    except Exception as exception:
        from traceback import format_exc, print_exc
        from click import UsageError, Abort
        from requests import exceptions
        from io import StringIO
        from pydantic import ValidationError
        from lean.models.errors import MoreInfoError

        logger = container.logger
        logger.debug(format_exc().strip())

        if isinstance(exception, ValidationError) and hasattr(exception, "input_value"):
            logger.debug("Value that failed validation:")
            logger.debug(exception.input_value)
            logger.error(f"Error: {exception}")
        elif isinstance(exception, MoreInfoError):
            logger.error(f"Error: {exception}")
            logger.error(f"Visit {exception.link} for more information")
        elif isinstance(exception, UsageError):
            io = StringIO()
            exception.show(file=io)

            exception_str = io.getvalue().strip()
            exception_str = exception_str.replace("Try 'lean", "\nTry 'lean")
            exception_str = exception_str.replace("for help.",
                                                  "for help or go to the following url for a list of common errors:\nhttps://www.lean.io/docs/v2/lean-cli/key-concepts/troubleshooting#02-Common-Errors")

            container.update_manager.warn_if_cli_outdated(force=True)

            logger.info(exception_str)
        elif isinstance(exception, Abort):
            logger.info("Aborted!")
        elif isinstance(exception, exceptions.ConnectionError):
            logger.error(f"Error: {exception}")
            logger.error("It looks like you don't have an internet connection, please check your system settings")
        else:
            logger.error(f"Error: {exception}")

        temp_manager = container.temp_manager
        if temp_manager.delete_temporary_directories_when_done:
            temp_manager.delete_temporary_directories()

        exit(1)
