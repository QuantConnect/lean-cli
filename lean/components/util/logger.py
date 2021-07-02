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

import platform
import sys
from typing import Any, List, Optional

import click
import maskpass
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn

from lean.models.logger import Option


class Logger:
    """The Logger class handles all output printing."""

    def __init__(self) -> None:
        """Creates a new Logger instance."""
        self._console = Console(markup=False, highlight=False, emoji=False)
        self.debug_logging_enabled = False

    def debug(self, message: Any) -> None:
        """Logs a debug message if debug logging is enabled.

        :param message: the message to log
        """
        if self.debug_logging_enabled:
            self._console.print(message, style="grey50")

    def info(self, message: Any) -> None:
        """Logs an info message.

        :param message: the message to log
        """
        self._console.print(message)

    def warn(self, message: Any) -> None:
        """Logs a warning message.

        :param message: the message to log
        """
        self._console.print(message, style="yellow")

    def error(self, message: Any) -> None:
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
            self.info(f"{text}: {options[0].label}")
            return options[0].id

        self.info(f"{text}:")
        for i, option in enumerate(options):
            self.info(f"{i + 1}) {option.label}")

        while True:
            user_input = click.prompt("Enter an option", type=str)

            try:
                index = int(user_input)
                if 0 < index <= len(options):
                    return options[index - 1].id
            except ValueError:
                option = next((option for option in options if option.label == user_input), None)
                if option is not None:
                    return option.id

            self.info("Please enter the number or label of an option")

    def prompt_password(self, text: str, default: Optional[str] = None) -> str:
        """Asks the user for a string value while masking the given input.

        :param text: the text to display before prompting
        :param default: the default value if no input is given
        :return: the given input
        """
        if default is not None:
            text = f"{text} [{'*' * len(default)}]"

        # Masking does not work properly in WSL2 and when the input is not coming from a keyboard
        if "microsoft" in platform.uname().release.lower() or not sys.stdin.isatty():
            return click.prompt(text, default=default, show_default=False)

        while True:
            user_input = maskpass.askpass(f"{text}: ")

            if len(user_input) == 0 and default is not None:
                return default

            if len(user_input) > 0:
                return user_input
