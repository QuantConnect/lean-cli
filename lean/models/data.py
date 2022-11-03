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

from abc import ABC
from datetime import datetime
from enum import Enum
from typing import List, Any, Optional, Dict, Set, Tuple, Pattern

from click import prompt
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


class DatasetCondition(WrappedBaseModel, ABC):
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
        # TODO: bug? ^ returns true even if option hasn't been resolved

        return option_results[self.option].value in self.values


class DatasetOrCondition(DatasetCondition):
    options: List[DatasetCondition]

    def check(self, option_results: Dict[str, OptionResult]) -> bool:
        # Check each option, if any return true then its true
        for option in self.options:
            if option.check(option_results):
                return True

        return False


class DatasetAndCondition(DatasetCondition):
    options: List[DatasetCondition]

    def check(self, option_results: Dict[str, OptionResult]) -> bool:
        # Check each option, if any return false, then its false
        for option in self.options:
            if not option.check(option_results):
                return False

        return True


class DatasetOption(WrappedBaseModel, ABC):
    id: str
    label: str
    description: str
    condition: Optional[DatasetCondition] = None

    @validator("condition", pre=True)
    def parse_condition(cls, value: Optional[Any]) -> Any:
        if value is None or isinstance(value, DatasetCondition):
            return value

        condition_types = {
            "oneof": DatasetOneOfCondition,
            "and": DatasetAndCondition,
            "or": DatasetOrCondition
        }

        conditionType = value["type"].lower()

        # Special AND/OR (Composition of conditions)
        if conditionType == "and" or conditionType == "or" :
            for i in range(0, len(value["options"])):
                option = value["options"][i]

                # Recurse as needed to flush out conditional tree
                value["options"][i] = cls.parse_condition(option)

        return condition_types[conditionType](**value)

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
    multiple: bool = False

    def configure_interactive(self) -> OptionResult:
        prompt_to_show = self.label
        if self.multiple:
            prompt_to_show += " (comma-separated)"

        user_input = prompt(prompt_to_show)
        return self.configure_non_interactive(user_input)

    def configure_non_interactive(self, user_input: str) -> OptionResult:
        if len(user_input.strip()) == 0:
            raise ValueError("Value cannot be a blank string")

        if self.multiple:
            parts = [v.strip() for v in user_input.split(",") if v.strip() != ""]
            value = [self.transform.apply(p) for p in parts]
            label = ", ".join(parts)
        else:
            value = self.transform.apply(user_input)
            label = user_input

        return OptionResult(value=value, label=label)

    def get_placeholder(self) -> str:
        if self.multiple:
            return "values"
        else:
            return "value"


class DatasetSelectOption(DatasetOption):
    choices: Dict[str, str]

    def configure_interactive(self) -> OptionResult:
        logger = container.logger

        keys = list(self.choices.keys())

        if len(keys) <= 5:
            key = logger.prompt_list(self.label, [Option(id=key, label=key) for key in keys])
        else:
            while True:
                user_input = prompt(f"{self.label} (example: {min(keys, key=len)})")

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
                error += f", please specify a value like '{min(keys, key=len)}'"

            raise ValueError(error)

        return OptionResult(value=self.choices[key], label=key)

    def get_placeholder(self) -> str:
        keys = list(self.choices.keys())

        if len(keys) <= 5:
            return "|".join(keys)
        else:
            return f"value (example: {min(keys, key=len)})"


class DatasetDateOption(DatasetOption):
    start_end: bool = False

    def configure_interactive(self) -> OptionResult:
        date = prompt(f"{self.label} (yyyyMMdd)", type=DateParameter())
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


class DatasetPathTemplates(WrappedBaseModel):
    all: List[str] = []
    latest: List[str] = []


class DatasetPath(WrappedBaseModel):
    condition: Optional[DatasetCondition] = None
    templates: DatasetPathTemplates

    @validator("condition", pre=True)
    def parse_condition(cls, value: Optional[Any]) -> Any:
        if value is None or isinstance(value, DatasetCondition):
            return value

        condition_types = {
            "oneof": DatasetOneOfCondition,
            "and": DatasetAndCondition,
            "or": DatasetOrCondition
        }

        conditionType = value["type"].lower()

        # Special AND/OR (Composition of conditions)
        if conditionType == "and" or conditionType == "or" :
            for i in range(0, len(value["options"])):
                option = value["options"][i]

                # Recurse as need to flush out conditional tree
                value["options"][i] = cls.parse_condition(option)

        return condition_types[conditionType](**value)


class Dataset(WrappedBaseModel):
    name: str
    vendor: str
    categories: List[str]
    options: List[DatasetOption]
    paths: List[DatasetPath]
    requires_security_master: bool

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

            # TODO: This is a hack around, does not respect option conditions for start-end
            elif option["type"] == "start-end":
                description_suffix = ""
                required_resolutions = ["tick", "second", "minute", "minute/second/tick"]

                resolution = next((o for o in options if o.id == "resolution"), None)
                if resolution is not None and isinstance(resolution, DatasetSelectOption):
                    if len(set(resolution.choices.values()) - set(required_resolutions)) > 0:
                        description_suffix = " (tick, second and minute resolutions only)"

                options.extend([
                    DatasetDateOption(
                        id="start",
                        label="Start date",
                        description="The inclusive end date of the data that you want to download" + description_suffix,
                        condition=DatasetOneOfCondition(option="resolution", values=required_resolutions),
                        start_end=True
                    ),
                    DatasetDateOption(
                        id="end",
                        label="End date",
                        description="The inclusive end date of the data that you want to download" + description_suffix,
                        condition=DatasetOneOfCondition(option="resolution", values=required_resolutions),
                        start_end=True
                    )
                ])
            else:
                options.append(option_types[option["type"]](**option))

        return options


class DataFile(WrappedBaseModel):
    file: str
    vendor: QCDataVendor


class DataFileGroup(WrappedBaseModel, ABC):
    prefix: str

    def get_valid_files(self, files_with_prefix: Optional[List[str]]) -> Set[str]:
        raise NotImplementedError()


class DataFileAllGroup(DataFileGroup):
    possible_files: Set[str]

    def get_valid_files(self, files_with_prefix: Optional[List[str]]) -> Set[str]:
        if files_with_prefix is not None:
            return self.possible_files.intersection(files_with_prefix)

        return self.possible_files


class DataFileLatestGroup(DataFileGroup):
    regex: Pattern

    def get_valid_files(self, files_with_prefix: Optional[List[str]]) -> Set[str]:
        if files_with_prefix is not None:
            matching_files = [file for file in files_with_prefix if self.regex.match(file) is not None]
            if len(matching_files) > 0:
                return {sorted(matching_files)[-1]}

        return set()


class Product(WrappedBaseModel):
    dataset: Dataset
    option_results: Dict[str, OptionResult]

    def get_data_files(self) -> List[str]:
        """Returns all data files for the given product configuration.

        :return: the list of files that need to be downloaded for this product
        """
        from multiprocessing import cpu_count
        from joblib import Parallel, delayed

        groups = []
        variables = {option_id: result.value for option_id, result in self.option_results.items()}

        multiple_option = next((o for o in self.dataset.options if isinstance(o, DatasetTextOption) and o.multiple),
                               None)
        if multiple_option is not None and multiple_option.id in self.option_results:
            result = self.option_results[multiple_option.id]

            for index in range(len(result.value)):
                groups.extend(self._get_data_file_groups({
                    **variables,
                    multiple_option.id: result.value[index]
                }))
        else:
            groups.extend(self._get_data_file_groups(variables))

        prefixes = set(group.prefix for group in groups)
        prefixes_to_files = {}

        parallel = Parallel(n_jobs=max(1, cpu_count() - 1), backend="threading")
        for prefix, files_with_prefix in parallel(delayed(self._list_files)(prefix) for prefix in prefixes):
            prefixes_to_files[prefix] = files_with_prefix

        data_files = set()
        for group in groups:
            data_files.update(group.get_valid_files(prefixes_to_files[group.prefix]))

        return sorted(list(data_files))

    def _get_data_file_groups(self, variables: Dict[str, Any]) -> List[DataFileGroup]:
        from dateutil.rrule import rrule, DAILY
        from re import split, compile

        groups = []

        for path in self.dataset.paths:
            if path.condition is None or path.condition.check(self.option_results):
                path_to_use = path
                break
        else:
            raise RuntimeError(f"No eligible path templates found")

        for template in path_to_use.templates.all:
            has_start_end = any(isinstance(o, DatasetDateOption) and o.start_end for o in self.dataset.options)
            start = variables.get("start", None)
            end = variables.get("end", None)

            possible_files = set()

            if has_start_end and start is not None and end is not None:
                variables_to_use = {**variables}
                for date in rrule(DAILY, dtstart=start, until=end):
                    variables_to_use["date"] = date
                    variables_to_use["year"] = date.strftime("%Y")
                    variables_to_use["month"] = date.strftime("%m")
                    variables_to_use["day"] = date.strftime("%d")
                    possible_files.add(self._render_template(template, variables_to_use))
            else:
                possible_files.add(self._render_template(template, variables))

            prefix = self._get_common_prefix(list(possible_files))

            groups.append(DataFileAllGroup(prefix=prefix, possible_files=possible_files))

        for regex_template in path_to_use.templates.latest:
            rendered_regex = self._render_template(regex_template, variables)

            prefix = split(r"[\\[\]()]", rendered_regex)[0]
            compiled_regex = compile(rendered_regex)

            groups.append(DataFileLatestGroup(prefix=prefix, regex=compiled_regex))

        return groups

    def _list_files(self, prefix: str) -> Tuple[str, Optional[List[str]]]:
        if len(prefix.split("/")) < 3:
            # Cannot get cloud directory listing less than 3 levels deep
            return prefix, None
        else:
            return prefix, container.api_client.data.list_files(prefix)

    def _get_common_prefix(self, values: List[str]) -> str:
        """Finds the common prefix in a list of strings.

        :param values: the strings to find the common prefix of
        :return: the common prefix of the given strings
        """
        shortest_value = min(values, key=len)

        for index, character in enumerate(shortest_value):
            for value in values:
                if value[index] != character:
                    return shortest_value[:index]

        return shortest_value

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
