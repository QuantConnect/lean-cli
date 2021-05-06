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

from typing import List, Optional

from lean.components.config.storage import Storage


class Option:
    """An Option instance manages a single value in a Storage instance."""

    def __init__(self, key: str, description: str, is_sensitive: bool, storage: Storage) -> None:
        """Creates a new StringOption instance.

        :param key: the name of the key of the option in the given Storage instance, using hyphens for separation
        :param description: a display-friendly description of the option
        :param is_sensitive: whether the contents of this option may be logged without masking it
        :param storage: the Storage instance to store this option in
        """
        self.key = key
        self.description = description
        self.is_sensitive = is_sensitive

        self._storage = storage
        self.location = storage.file

    def get_value(self, default: Optional[str] = None) -> Optional[str]:
        """Retrieves the current value of the option.

        :param default: the value to return if the option is not set
        :return: the current value of the option, or the given default if the option is not set
        """
        return self._storage.get(self.key, default)

    def set_value(self, value: str) -> None:
        """Sets the new value of the option.

        :param value: the non-empty new value of the option
        """
        if value == "":
            raise ValueError("Value cannot be empty")

        self._storage.set(self.key, value)

    def unset(self) -> None:
        """Unsets any value of the option."""
        self._storage.delete(self.key)


class ChoiceOption(Option):
    """A variant of Option where only a few values are allowed.

    The allowed values are considered to be case insensitive.
    """

    def __init__(self,
                 key: str,
                 description: str,
                 allowed_values: List[str],
                 is_sensitive: bool,
                 storage: Storage) -> None:
        """Creates a new ChoiceOption instance.

        :param key: the name of the key of the option in the given file, should use hyphens for separation
        :param description: a display-friendly description of the option
        :param allowed_values: the values which can be set
        :param is_sensitive: whether the contents of this option may be logged without masking it
        :param storage: the Storage instance to store this option in
        """
        self.allowed_values = allowed_values

        if description.endswith("."):
            description = description[:-1]
        description = description + f" (allowed values: {', '.join(allowed_values)})."

        super().__init__(key, description, is_sensitive, storage)

    def set_value(self, value: str) -> None:
        """Sets the new value of the option.

        :param value: the new value of the option, must be one of this option's allowed values
        """
        matching_value = next((x for x in self.allowed_values if x.lower() == value.lower()), None)

        if matching_value is None:
            raise ValueError(
                f"Invalid value, '{self.key}' only accepts the following values: {', '.join(self.allowed_values)}")

        super().set_value(matching_value)
