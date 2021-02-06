import json
from pathlib import Path
from typing import Any, List

import click

from lean.constants import CLI_CONFIG_FILE, CREDENTIALS_FILE, GLOBAL_CONFIG_DIR


class GlobalConfig(dict):
    """A GlobalConfig instance manages the data in a single file in ~/.lean."""

    def __init__(self, file_name: str) -> None:
        """Create a GlobalConfig instance for the ~/.lean/<file_name> file.

        If the file exists already, its data is loaded into the instance.

        :param file_name: the file in ~/.lean to create the GlobalConfig instance for
        """
        super().__init__()

        self.path = Path.home() / GLOBAL_CONFIG_DIR / file_name

        if self.path.exists():
            with open(self.path) as file:
                self.update(json.load(file))

    def save(self) -> None:
        """Save the modified data to the underlying file."""
        with open(self.path, "w+") as file:
            json.dump(self, file, indent=4)

    def clear(self) -> None:
        """Clear the GlobalConfig instance and delete the underlying file."""
        super(GlobalConfig, self).clear()

        if self.path.exists():
            self.path.unlink()


class StringOption:
    """A StringOption instance manages a single option in a single file in ~/.lean."""

    def __init__(self, key: str, description: str, file_name: str) -> None:
        """Create a new StringOption instance for the option with key <name> in ~/.lean/<file_name>.

        :param key: the name of the key of the option in the given file, should use hyphens for separation
        :param description: a display-friendly description of the option
        :param file_name: the file in ~/.lean to store the option in
        """
        self.key = key
        self.description = description
        self.file_name = file_name

    def get_value(self, default: Any = None) -> str:
        """Retrieve the current value of the option as it appears in the ~/.lean/<file_name> file.

        :param default: the value to return if the option is not set
        :return: the current value of the option, or the given default if the option is not set
        """
        config = GlobalConfig(self.file_name)
        return config[self.key] if self.key in config else default

    def set_value(self, value: str) -> None:
        """Set the new value of the option.

        A ClickException is thrown if the new value is invalid.

        :param value: the new value of the option
        """
        if value == "":
            raise click.ClickException("Value cannot be empty")

        config = GlobalConfig(self.file_name)
        config[self.key] = value
        config.save()


class ChoiceOption(StringOption):
    """A variant of StringOption where only a few values are allowed.

    The allowed values are considered to be case insensitive.
    """

    def __init__(self, key: str, description: str, file_name: str, allowed_values: List[str]) -> None:
        """Create a new ChoiceOption instance.

        :param key: the name of the key of the option in the given file, should use hyphens for separation
        :param description: a display-friendly description of the option
        :param file_name: the file in ~/.lean to store the option in
        :param allowed_values: the values which can be set
        """
        self.allowed_values = allowed_values

        if description.endswith("."):
            description = description[:-1]
        description = description + f" (allowed values: {', '.join(allowed_values)})."

        super().__init__(key, description, file_name)

    def set_value(self, value: str) -> None:
        """Set the new value of the option.

        A ClickException is thrown if the new value is not one of the allowed values.

        :param value: the new value of the option
        """
        matching_value = next((x for x in self.allowed_values if x.lower() == value.lower()), None)

        if matching_value is None:
            raise click.ClickException(
                f"Invalid value, '{self.key}' only accepts the following values: {', '.join(self.allowed_values)}")

        super(ChoiceOption, self).set_value(matching_value)


user_id_option = StringOption("user-id",
                              "The user id used when making authenticated requests to the QuantConnect API.",
                              CREDENTIALS_FILE)

api_token_option = StringOption("api-token",
                                "The API token used when making authenticated requests to the QuantConnect API.",
                                CREDENTIALS_FILE)

default_language_option = ChoiceOption("default-language",
                                       "The default language used when creating new projects.",
                                       CLI_CONFIG_FILE,
                                       ["python", "csharp"])

all_options = [user_id_option, api_token_option, default_language_option]
