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

from unittest import mock

import pytest

from lean.models.options import ChoiceOption, Option


def test_option_get_value_returns_value_from_storage() -> None:
    storage = mock.Mock()
    storage.get.return_value = "123"

    option = Option("my-key", "Documentation for my-key.", False, storage)

    assert option.get_value() == "123"


def test_option_set_value_writes_to_storage() -> None:
    storage = mock.Mock()

    option = Option("my-key", "Documentation for my-key.", False, storage)
    option.set_value("123")

    storage.set.assert_called_once_with("my-key", "123")


def test_option_set_value_raises_when_new_value_blank() -> None:
    storage = mock.Mock()

    option = Option("my-key", "Documentation for my-key.", False, storage)

    with pytest.raises(Exception):
        option.set_value("")

    storage.set.assert_not_called()


def test_option_unset_deletes_key_from_storage() -> None:
    storage = mock.Mock()

    option = Option("my-key", "Documentation for my-key.", False, storage)
    option.unset()

    storage.delete.assert_called_once_with("my-key")


def test_choice_option_adds_allowed_values_to_description() -> None:
    storage = mock.Mock()

    option = ChoiceOption("my-key", "Documentation for my-key.", ["option1", "option2"], False, storage)

    assert "option1" in option.description
    assert "option2" in option.description


@pytest.mark.parametrize("new_value,normalized",
                         [("option1", "option1"), ("Option1", "option1"), ("OPTION1", "option1")])
def test_choice_option_set_value_normalizes_case(new_value: str, normalized: str) -> None:
    storage = mock.Mock()

    option = ChoiceOption("my-key", "Documentation for my-key.", ["option1", "option2"], False, storage)
    option.set_value(new_value)

    storage.set.assert_called_once_with("my-key", normalized)


def test_choice_option_set_value_raises_when_new_value_not_in_allowed_values() -> None:
    storage = mock.Mock()

    option = ChoiceOption("my-key", "Documentation for my-key.", ["option1", "option2"], False, storage)

    with pytest.raises(Exception):
        option.set_value("option3")

    storage.set.assert_not_called()
