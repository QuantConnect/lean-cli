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
        self.debug_logging_enabled = False

    def info(self, message: str, newline: bool = True) -> None:
        """Logs a message to stdout.

        :param message: the message to log
        :param newline: whether a newline character should be appended to the message
        """
        print(message, end="\n" if newline else "")

    def debug(self, message: str, newline: bool = True) -> None:
        """Logs a debug message to stdout if debug logging is enabled.

        :param message: the message to log
        :param newline: whether a newline character should be appended to the message
        """
        if self.debug_logging_enabled:
            self.info(message, newline=newline)

    def error(self, message: str, newline: bool = True) -> None:
        """Logs a message to stderr.

        :param message: the message to log
        :param newline: whether a newline character should be appended to the message
        """
        print(message, end="\n" if newline else "", file=sys.stderr)

    def flush(self) -> None:
        """Flushes stdout and stderr."""
        sys.stdout.flush()
        sys.stderr.flush()
