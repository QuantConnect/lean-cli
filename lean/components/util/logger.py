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

from typing import Any, List

import click
from rich.console import Console, RenderableType
from rich.progress import BarColumn, Progress, TextColumn

from lean.models.logger import Option


class Logger:
    """The Logger class handles all output printing."""

    def __init__(self) -> None:
        """Creates a new Logger instance."""
        self._console = Console(markup=False, highlight=False, emoji=False)
        self._debug_logging_enabled = False

    def enable_debug_logging(self) -> None:
        """Enables debug messages to be printed."""
        self._debug_logging_enabled = True

    def debug(self, message: str) -> None:
        """Logs a debug message if debug logging is enabled.

        :param message: the message to log
        """
        if self._debug_logging_enabled:
            self._console.print(message, style="grey50")

    def info(self, message: RenderableType) -> None:
        """Logs an info message.

        :param message: the message to log
        """
        self._console.print(message)

    def warn(self, message: str) -> None:
        """Logs a warning message.

        :param message: the message to log
        """
        self._console.print(message, style="yellow")

    def error(self, message: RenderableType) -> None:
        """Logs an error message.

        :param message: the message to log
        """
        self._console.print(message, style="red")

    def progress(self) -> Progress:
        """Creates a Progress instance.

        :return: a Progress instance which can be used to display progress bars
        """
        progress = Progress(TextColumn(""), BarColumn(), TextColumn("{task.percentage:0.0f}%"), console=self._console)
        progress.start()
        return progress

    def prompt_list(self, text: str, options: List[Option]) -> Any:
        """Asks the user to select an option from a list of possible options.

        The user will not be prompted for input if there is only a single option.

        :param text: the text to display before prompting
        :param options: the available options
        :return: the chosen option's id
        """
        if len(options) == 1:
            return options[0].id

        self.info(f"{text}:")
        for i, option in enumerate(options):
            self.info(f"{i + 1}) {option.label}")

        number = click.prompt("Enter a number", type=click.IntRange(min=1, max=len(options)))
        return options[number - 1].id
