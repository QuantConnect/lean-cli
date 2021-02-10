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
