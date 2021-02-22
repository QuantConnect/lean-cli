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

import sys


class Logger:
    """A Logger logs messages."""

    def __init__(self) -> None:
        """Creates a new Logger instance."""
        self._debug_logging_enabled = False

    def enable_debug_logging(self) -> None:
        """Enables debug messages to be printed."""
        self._debug_logging_enabled = True

    def debug(self, message: str) -> None:
        """Logs a debug message to stdout if debug logging is enabled.

        :param message: the message to log
        """
        if self._debug_logging_enabled:
            print(message)

    def info(self, message: str) -> None:
        """Logs a message to stdout.

        :param message: the message to log
        """
        print(message)

    def warn(self, message: str) -> None:
        """Logs a warning message to stderr.

        :param message: the message to log
        """
        print(message, file=sys.stderr)

    def error(self, message: str) -> None:
        """Logs a message to stderr.

        :param message: the message to log
        """
        print(message, file=sys.stderr)
