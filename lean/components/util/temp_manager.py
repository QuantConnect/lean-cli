import shutil
import tempfile
from pathlib import Path


class TempManager:
    """The TempManager class provides access to temporary directories."""

    def __init__(self) -> None:
        """Creates a new TempManager instance."""
        self._temporary_directories = []

    def create_temporary_directory(self) -> Path:
        """Returns the path to an empty temporary directory.

        :return: a path to an empty temporary directory
        """
        path = Path(tempfile.mkdtemp())
        self._temporary_directories.append(path)
        return path

    def delete_temporary_directories(self) -> None:
        """Deletes temporary directories that were created while the CLI ran.

        Only the files that the user can delete are deleted, any permission errors are ignored.
        """
        for path in self._temporary_directories:
            shutil.rmtree(path, ignore_errors=True)
