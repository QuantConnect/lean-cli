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

from lean.components.config.cli_config_manager import CLIConfigManager


def test_get_option_by_key_returns_option_with_matching_key() -> None:
    manager = CLIConfigManager(mock.Mock(), mock.Mock())

    for key in ["user-id", "api-token", "default-language"]:
        assert manager.get_option_by_key(key).key == key


def test_get_option_by_key_raises_error_when_no_option_with_matching_key_exists() -> None:
    manager = CLIConfigManager(mock.Mock(), mock.Mock())

    with pytest.raises(Exception):
        manager.get_option_by_key("this-option-does-not-exist")
