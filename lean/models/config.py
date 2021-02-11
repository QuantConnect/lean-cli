from enum import Enum


class DebuggingMethod(str, Enum):
    """The debugging methods supported by the CLI.

    The name of the members is the internal name, the value is what's passed to the LEAN engine.
    """
    PyCharm = "PyCharm"
    PTVSD = "PTVSD"
    Mono = "LocalCmdline"
