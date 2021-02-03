"""This module contains functions to manage the global configuration files in ~/.lean."""

import json
from pathlib import Path


class GlobalConfig(dict):
    """A GlobalConfig instance manages the data in a single file in ~/.lean."""

    def __init__(self, file_name: str) -> None:
        """Create a GlobalConfig instance for the ~/.lean/<file_name> file.

        If the file exists already, its data is loaded into the instance.
        """
        self.path = Path.home() / ".lean" / file_name

        if self.path.exists():
            with open(self.path) as file:
                self.update(json.load(file))

    def save(self) -> None:
        """Save the modified data to the underlying file."""
        with open(self.path, "w+") as file:
            json.dump(self, file, indent=4)

    def clear(self) -> None:
        """Clear the GlobalConfig instance and deletes the underlying file."""
        super(GlobalConfig, self).clear()

        if self.path.exists():
            self.path.unlink()
