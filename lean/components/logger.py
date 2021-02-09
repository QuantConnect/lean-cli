import sys

import click


class Logger:
    """A Logger logs messages."""

    def __init__(self) -> None:
        """Creates a new Logger instance."""
        self._debug_logging_enabled = False

    def info(self, message: str, newline: bool = True) -> None:
        """Logs a message to stdout.

        :param message: the message to log
        :param newline: whether a newline character should be appended to the message
        """
        click.echo(message, nl=newline)

    def debug(self, message: str, newline: bool = True) -> None:
        """Logs a debug message to stdout if debug logging is enabled.

        :param message: the message to log
        :param newline: whether a newline character should be appended to the message
        """
        if self._debug_logging_enabled:
            self.info(message, newline=newline)

    def error(self, message: str, newline: bool = True) -> None:
        """Logs a message to stderr.

        :param message: the message to log
        :param newline: whether a newline character should be appended to the message
        """
        click.echo(message, nl=newline, err=True)

    def flush(self) -> None:
        """Flushes stdout and stderr."""
        sys.stdout.flush()
        sys.stderr.flush()

    def enable_debug_logging(self) -> None:
        """Enables all debug messages after the call to this method to be printed to stdout."""
        self._debug_logging_enabled = True
