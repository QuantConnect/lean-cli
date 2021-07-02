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

import abc
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Any, Optional, Dict

import click
from dateutil.rrule import rrule, DAILY
from pydantic import validator

from lean.click import DateParameter
from lean.container import container
from lean.models.api import QCDataVendor
from lean.models.logger import Option
from lean.models.pydantic import WrappedBaseModel


class OptionResult(WrappedBaseModel):
    """The OptionResult class represents an option's result with an internal value and a display-friendly label."""
    value: Any
    label: str


class DatasetCondition(WrappedBaseModel, abc.ABC):
    def check(self, option_results: Dict[str, OptionResult]) -> bool:
        """Evaluates the condition against a set of options.

        If there is not enough information because of missing options the condition evaluates to True.

        :param option_results: the option id -> option result dictionary to evaluate against
        :return: False if the condition definitely
        """
        raise NotImplementedError()


class DatasetOneOfCondition(DatasetCondition):
    option: str
    values: List[str]

    def check(self, option_results: Dict[str, OptionResult]) -> bool:
        if self.option not in option_results:
            return True

        return option_results[self.option].value in self.values


class DatasetOption(WrappedBaseModel, abc.ABC):
    id: str
    label: str
    description: str
    condition: Optional[DatasetCondition] = None

    @validator("condition", pre=True)
    def parse_condition(cls, value: Optional[Any]) -> Any:
        if value is None or isinstance(value, DatasetCondition):
            return value

        condition_types = {
            "oneOf": DatasetOneOfCondition
        }

        return condition_types[value["type"]](**value)

    def configure_interactive(self) -> OptionResult:
        """Prompt the user for input to configure this option.

        :return: the parsed result
        """
        raise NotImplementedError()

    def configure_non_interactive(self, user_input: str) -> OptionResult:
        """Parses user input without prompting for anything.

        Raises a ValueError with a descriptive error message if the given input is invalid.

        :param user_input: the input given by the user
        :return: the parsed result
        """
        raise NotImplementedError()

    def get_placeholder(self) -> str:
        """Returns the placeholder of this option.

        :return: the value to show in the place of "value" when documenting this option as "--id <value>"
        """
        raise NotImplementedError()


class DatasetTextOptionTransform(str, Enum):
    Lowercase = "lowercase"
    Uppercase = "uppercase"

    def apply(self, value: str) -> str:
        if self == DatasetTextOptionTransform.Lowercase:
            return value.lower()
        elif self == DatasetTextOptionTransform.Uppercase:
            return value.upper()


class DatasetTextOption(DatasetOption):
    transform: DatasetTextOptionTransform

    def configure_interactive(self) -> OptionResult:
        user_input = click.prompt(self.label)
        return self.configure_non_interactive(user_input)

    def configure_non_interactive(self, user_input: str) -> OptionResult:
        if len(user_input.strip()) == 0:
            raise ValueError("Value cannot be a blank string")

        return OptionResult(value=self.transform.apply(user_input), label=user_input)

    def get_placeholder(self) -> str:
        return "value"


class DatasetSelectOption(DatasetOption):
    choices: Dict[str, str]

    def configure_interactive(self) -> OptionResult:
        logger = container.logger()

        keys = list(self.choices.keys())

        if len(keys) <= 5:
            key = logger.prompt_list(self.label, [Option(id=key, label=key) for key in keys])
        else:
            while True:
                user_input = click.prompt(f"{self.label} (example: {self._get_shortest_value(keys)})")

                key = next((key for key in keys if key.lower() == user_input.lower()), None)
                if key is not None:
                    break

                logger.info(f"Error: '{user_input}' is not a valid option")

        return OptionResult(value=self.choices[key], label=key)

    def configure_non_interactive(self, user_input: str) -> OptionResult:
        keys = list(self.choices.keys())

        key = next((key for key in keys if key.lower() == user_input.lower()), None)
        if key is None:
            error = f"'{user_input}' is not a valid option"

            if len(keys) <= 5:
                error += f", please choose one of the following: {', '.join(keys)}"
            else:
                error += f", please specify a value like '{self._get_shortest_value(keys)}'"

            raise ValueError(error)

        return OptionResult(value=self.choices[key], label=key)

    def get_placeholder(self) -> str:
        keys = list(self.choices.keys())

        if len(keys) <= 5:
            return "|".join(keys)
        else:
            return f"value (example: {self._get_shortest_value(keys)})"

    def _get_shortest_value(self, values: List[str]) -> str:
        return sorted(values, key=lambda value: len(value))[0]


class DatasetDateOption(DatasetOption):
    def configure_interactive(self) -> OptionResult:
        date = click.prompt(f"{self.label} (yyyyMMdd)", type=DateParameter())
        return OptionResult(value=date, label=date.strftime("%Y-%m-%d"))

    def configure_non_interactive(self, user_input: str) -> OptionResult:
        for date_format in ["%Y%m%d", "%Y-%m-%d"]:
            try:
                date = datetime.strptime(user_input, date_format)
                return OptionResult(value=date, label=date.strftime("%Y-%m-%d"))
            except ValueError:
                pass

        raise ValueError(f"'{user_input}' does not match the yyyyMMdd format")

    def get_placeholder(self) -> str:
        return "yyyyMMdd"


class DatasetPath(WrappedBaseModel):
    condition: Optional[DatasetCondition] = None
    templates: List[str]

    @validator("condition", pre=True)
    def parse_condition(cls, value: Optional[Any]) -> Any:
        if value is None or isinstance(value, DatasetCondition):
            return value

        condition_types = {
            "oneOf": DatasetOneOfCondition
        }

        return condition_types[value["type"]](**value)


class Dataset(WrappedBaseModel):
    name: str
    vendor: str
    categories: List[str]
    requiresSecurityMaster: bool
    options: List[DatasetOption]
    paths: List[DatasetPath]

    @validator("options", pre=True)
    def parse_options(cls, values: List[Any]) -> List[Any]:
        option_types = {
            "text": DatasetTextOption,
            "select": DatasetSelectOption,
            "date": DatasetDateOption
        }

        options = []
        for option in values:
            if isinstance(option, DatasetOption):
                options.append(option)
            else:
                options.append(option_types[option["type"]](**option))

        return options


class DataFile(WrappedBaseModel):
    file: str
    vendor: QCDataVendor


class Product(WrappedBaseModel):
    dataset: Dataset
    option_results: Dict[str, OptionResult]

    def get_data_files(self) -> List[str]:
        """Returns all data files for the given product configuration.

        :return: the list of files that need to be downloaded for this product
        """
        api_client = container.api_client()

        for path in self.dataset.paths:
            if path.condition is None or path.condition.check(self.option_results):
                templates = path.templates
                break
        else:
            raise RuntimeError(f"No eligible path templates found")

        files = set()

        for template in templates:
            variables = {option_id: result.value for option_id, result in self.option_results.items()}

            start = self.option_results.get("start", None)
            end = self.option_results.get("end", None)

            if start is not None and end is not None:
                for date in rrule(DAILY, dtstart=start.value, until=end.value):
                    variables["date"] = date.strftime("%Y%m%d")
                    files.add(self._render_template(template, variables))
            else:
                files.add(self._render_template(template, variables))

        available_files_by_parent = {}
        for parent in set(Path(file).parent.as_posix() for file in files):
            if len(parent.split("/")) < 3:
                # Cannot get cloud directory listing less than 3 levels deep
                continue

            available_files_by_parent[parent] = api_client.data.list_files(parent + "/")

        data_files = set()
        for file in files:
            parent = Path(file).parent.as_posix()
            if parent not in available_files_by_parent or file in available_files_by_parent[parent]:
                data_files.add(file)

        return sorted(list(data_files))

    def _render_template(self, template: str, variables: Dict[str, str]) -> str:
        """Renders a template string with variables.

        Variables can be referenced in the template by putting accolades around them.
        Example template: "path/to/{date}.zip" (date is a referenced variable here)

        :param template: the template to render
        :param variables: the variables that are accessible to the template
        :return: the rendered template
        """
        for key, value in variables.items():
            if isinstance(value, datetime):
                value = value.strftime("%Y%m%d")

            template = template.replace("{" + key + "}", str(value))

        return template
