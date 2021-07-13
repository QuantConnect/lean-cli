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
import re
from datetime import datetime
from typing import List, Dict, Optional, Union, Set, Pattern

import pytest

from lean.models.data import DatasetOneOfCondition, OptionResult, DatasetTextOption, DatasetTextOptionTransform, \
    DatasetSelectOption, DatasetDateOption, DataFileAllGroup, DataFileLatestGroup


@pytest.mark.parametrize("option,values,results,expected", [
    ("option", ["Value1", "Value2", "Value3"], {"option": "Value1"}, True),
    ("option", ["Value1", "Value2", "Value3"], {}, True),
    ("option", ["Value1", "Value2", "Value3"], {"option": "value1"}, False),
    ("option", ["Value1", "Value2", "Value3"], {"option": "Value4"}, False)
])
def test_dataset_one_of_condition_check_works_correctly(option: str,
                                                        values: List[str],
                                                        results: Dict[str, str],
                                                        expected: bool) -> None:
    condition = DatasetOneOfCondition(option=option, values=values)
    actual = condition.check({key: OptionResult(value=value, label=value) for key, value in results.items()})

    assert actual == expected


@pytest.mark.parametrize("transform,value,expected", [
    (DatasetTextOptionTransform.Lowercase, "input", "input"),
    (DatasetTextOptionTransform.Lowercase, "Input", "input"),
    (DatasetTextOptionTransform.Lowercase, "INPUT", "input"),
    (DatasetTextOptionTransform.Uppercase, "input", "INPUT"),
    (DatasetTextOptionTransform.Uppercase, "Input", "INPUT"),
    (DatasetTextOptionTransform.Uppercase, "INPUT", "INPUT")
])
def test_dataset_text_option_transform_apply_works_correctly(transform: DatasetTextOptionTransform,
                                                             value: str,
                                                             expected: str) -> None:
    assert transform.apply(value) == expected


@pytest.mark.parametrize("value,transform,expected_value,expected_label", [
    ("input", DatasetTextOptionTransform.Lowercase, "input", "input"),
    ("Input", DatasetTextOptionTransform.Lowercase, "input", "Input"),
    ("", DatasetTextOptionTransform.Lowercase, None, None),
    (" ", DatasetTextOptionTransform.Lowercase, None, None),
    ("INPUT", DatasetTextOptionTransform.Uppercase, "INPUT", "INPUT"),
    ("Input", DatasetTextOptionTransform.Uppercase, "INPUT", "Input"),
    ("", DatasetTextOptionTransform.Uppercase, None, None),
    (" ", DatasetTextOptionTransform.Uppercase, None, None),
    ("input1,input2", DatasetTextOptionTransform.Lowercase, ["input1", "input2"], "input1, input2"),
    ("input1, input2", DatasetTextOptionTransform.Lowercase, ["input1", "input2"], "input1, input2"),
    ("input1,,input2,", DatasetTextOptionTransform.Lowercase, ["input1", "input2"], "input1, input2"),
    ("Input1,Input2", DatasetTextOptionTransform.Lowercase, ["input1", "input2"], "Input1, Input2"),
    ("Input1, Input2", DatasetTextOptionTransform.Lowercase, ["input1", "input2"], "Input1, Input2"),
    ("Input1,,Input2,", DatasetTextOptionTransform.Lowercase, ["input1", "input2"], "Input1, Input2"),
    ("INPUT1,INPUT2", DatasetTextOptionTransform.Uppercase, ["INPUT1", "INPUT2"], "INPUT1, INPUT2"),
    ("INPUT1, INPUT2", DatasetTextOptionTransform.Uppercase, ["INPUT1", "INPUT2"], "INPUT1, INPUT2"),
    ("INPUT1,,INPUT2,", DatasetTextOptionTransform.Uppercase, ["INPUT1", "INPUT2"], "INPUT1, INPUT2"),
    ("Input1,Input2", DatasetTextOptionTransform.Uppercase, ["INPUT1", "INPUT2"], "Input1, Input2"),
    ("Input1, Input2", DatasetTextOptionTransform.Uppercase, ["INPUT1", "INPUT2"], "Input1, Input2"),
    ("Input1,,Input2,", DatasetTextOptionTransform.Uppercase, ["INPUT1", "INPUT2"], "Input1, Input2")
])
def test_dataset_text_option_configure_non_interactive_works_correctly(value: str,
                                                                       transform: DatasetTextOptionTransform,
                                                                       expected_value: Optional[Union[str, List[str]]],
                                                                       expected_label: Optional[str]) -> None:
    option = DatasetTextOption(id="id",
                               label="label",
                               description="description",
                               transform=transform,
                               multiple=isinstance(expected_value, list))

    if expected_value is None and expected_label is None:
        with pytest.raises(ValueError):
            option.configure_non_interactive(value)
    else:
        result = option.configure_non_interactive(value)

        assert result.value == expected_value
        assert result.label == expected_label


@pytest.mark.parametrize("multiple,expected_placeholder", [(False, "value"), (True, "values")])
def test_dataset_text_option_get_placeholder_works_correctly(multiple: bool, expected_placeholder: str) -> None:
    option = DatasetTextOption(id="id",
                               label="label",
                               description="description",
                               transform=DatasetTextOptionTransform.Lowercase,
                               multiple=multiple)

    assert option.get_placeholder() == expected_placeholder


@pytest.mark.parametrize("value,choices,expected_value,expected_label", [
    ("Choice1", {"Choice1": "Internal1"}, "Internal1", "Choice1"),
    ("choice1", {"Choice1": "Internal1"}, "Internal1", "Choice1"),
    ("Choice2", {"Choice1": "Internal1"}, None, None)
])
def test_dataset_select_option_configure_non_interactive_works_correctly(value: str,
                                                                         choices: Dict[str, str],
                                                                         expected_value: Optional[str],
                                                                         expected_label: Optional[str]) -> None:
    option = DatasetSelectOption(id="id", label="label", description="description", choices=choices)

    if expected_value is None and expected_label is None:
        with pytest.raises(ValueError):
            option.configure_non_interactive(value)
    else:
        result = option.configure_non_interactive(value)

        assert result.value == expected_value
        assert result.label == expected_label


@pytest.mark.parametrize("choices,placeholder", [
    ({
         "Choice1": "Internal1",
         "Choice2": "Internal2",
         "Choice3": "Internal3",
         "Choice4": "Internal4"
     }, "Choice1|Choice2|Choice3|Choice4"),
    ({
         "Choice1": "Internal1",
         "Choice2": "Internal2",
         "Choice3": "Internal3",
         "Choice4": "Internal4",
         "Choice5": "Internal5"
     }, "Choice1|Choice2|Choice3|Choice4|Choice5"),
    ({
         "Choice1": "Internal1",
         "Choice2": "Internal2",
         "Choice3": "Internal3",
         "Choice4": "Internal4",
         "Choice5": "Internal5",
         "Choice6": "Internal6"
     }, "value (example: Choice1)"),
    ({
         "LongChoice1": "Internal1",
         "Choice2": "Internal2",
         "Choice3": "Internal3",
         "Choice4": "Internal4",
         "Choice5": "Internal5",
         "Choice6": "Internal6"
     }, "value (example: Choice2)")
])
def test_dataset_select_option_get_placeholder_works_correctly(choices: Dict[str, str], placeholder: str) -> None:
    option = DatasetSelectOption(id="id", label="label", description="description", choices=choices)

    assert option.get_placeholder() == placeholder


@pytest.mark.parametrize("value,expected_value,expected_label", [
    ("20200101", datetime(2020, 1, 1), "2020-01-01"),
    ("2020-01-01", datetime(2020, 1, 1), "2020-01-01"),
    ("2020-01-32", None, None),
    ("2020", None, None),
    ("", None, None)
])
def test_dataset_date_option_configure_non_interactive_works_correctly(value: str,
                                                                       expected_value: Optional[datetime],
                                                                       expected_label: Optional[str]) -> None:
    option = DatasetDateOption(id="id", label="label", description="description")

    if expected_value is None and expected_label is None:
        with pytest.raises(ValueError):
            option.configure_non_interactive(value)
    else:
        result = option.configure_non_interactive(value)

        assert result.value == expected_value
        assert result.label == expected_label


def test_dataset_date_option_get_placeholder_works_correctly() -> None:
    option = DatasetDateOption(id="id", label="label", description="description")

    assert option.get_placeholder() == "yyyyMMdd"


@pytest.mark.parametrize("prefix,possible_files,files_with_prefix,expected_result", [
    ("/data", {"/data/a.csv", "/data/b.csv"}, ["/data/a.csv"], {"/data/a.csv"}),
    ("/data", {"/data/a.csv", "/data/b.csv"}, ["/data/c.csv"], set()),
    ("/data", {"/data/a.csv", "/data/b.csv"}, [], set()),
    ("/data", {"/data/a.csv", "/data/b.csv"}, None, {"/data/a.csv", "/data/b.csv"})
])
def test_data_file_all_group_get_valid_files_works_correctly(prefix: str,
                                                             possible_files: Set[str],
                                                             files_with_prefix: Optional[List[str]],
                                                             expected_result: Set[str]) -> None:
    group = DataFileAllGroup(prefix=prefix, possible_files=possible_files)

    assert group.get_valid_files(files_with_prefix) == expected_result


@pytest.mark.parametrize("prefix,regex,files_with_prefix,expected_result", [
    (
        "/data",
        re.compile(r"/data/\d+.csv"),
        ["/data/x999999.csv", "/data/20200101.csv", "/data/20210101.csv"],
        {"/data/20210101.csv"}
    ),
    ("/data", re.compile(r"/data/\d+.csv"), ["/data/aapl.csv", "/data/msft.csv"], set()),
    ("/data", re.compile(r"/data/\d+.csv"), None, set())
])
def test_data_file_latest_group_get_valid_files_works_correctly(prefix: str,
                                                                regex: Pattern,
                                                                files_with_prefix: Optional[List[str]],
                                                                expected_result: Set[str]) -> None:
    group = DataFileLatestGroup(prefix=prefix, regex=regex)

    assert group.get_valid_files(files_with_prefix) == expected_result
