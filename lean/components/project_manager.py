from pathlib import Path


class ProjectManager:
    """The ProjectManager class provides utilities for finding specific files in projects."""

    def find_algorithm_file(self, input: Path) -> Path:
        """Returns the path to the file containing the algorithm.

        Raises an error if the algorithm file cannot be found.

        :param input: the path to the algorithm or the path to the project
        :return: the path to the file containing the algorithm
        """
        if input.is_file():
            return input

        for file_name in ["main.py", "Main.cs"]:
            target_file = input / file_name
            if target_file.exists():
                return target_file

        raise ValueError("The specified project does not contain a main.py or Main.cs file")
