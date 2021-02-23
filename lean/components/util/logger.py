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

from typing import Any, Union

from rich.console import Console, RenderableType
from tqdm import tqdm


class Logger:
    """The Logger class handles all output printing."""

    def __init__(self) -> None:
        """Creates a new Logger instance."""
        self._debug_logging_enabled = False

        self._stdout_console = Console(stderr=False)
        self._stderr_console = Console(stderr=True)

    def enable_debug_logging(self) -> None:
        """Enables debug messages to be printed."""
        self._debug_logging_enabled = True

    def debug(self, message: str) -> None:
        """Logs a debug message to stdout if debug logging is enabled.

        :param message: the message to log
        """
        if self._debug_logging_enabled:
            self._stdout_console.print(message)

    def info(self, message: Union[str, RenderableType], enable_markup: bool = False) -> None:
        """Logs a message to stdout.

        :param message: the message to log
        :param enable_markup: True if rich's markup should be enabled, False if not
        """
        if enable_markup:
            self._stdout_console.print(message)
        else:
            print(message)

    def warn(self, message: str) -> None:
        """Logs a warning message to stderr.

        :param message: the message to log
        """
        self._stderr_console.print(f"[orange1]{message}[/orange1]")

    def error(self, message: str) -> None:
        """Logs a message to stderr.

        :param message: the message to log
        """
        self._stderr_console.print(f"[red]{message}[/red]")

    def progress(self, total: Any) -> tqdm:
        """Creates a progress bar.

        :param total: the progress bar's end amount
        :return: a tqdm instance containing the progress bar that is being displayed
        """
        return tqdm(total=total, ncols=50, bar_format="[{bar}] {percentage:1.0f}%", ascii=" =")
