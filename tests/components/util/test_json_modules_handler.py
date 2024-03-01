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
from unittest.mock import MagicMock

import pytest

from lean.components.util.json_modules_handler import find_module
from lean.constants import MODULE_CLI_PLATFORM, MODULE_BROKERAGE
from lean.models.json_module import JsonModule
from tests.test_helpers import create_fake_lean_cli_directory


@pytest.mark.parametrize("id,display,search_name", [("ads", "binAnce", "BiNAnce"),
                                                    ("binAnce", "a", "BiNAnce"),
                                                    ("ads", "binAnce", "QC.Brokerage.Binance.BiNAnce"),
                                                    ("binAnce", "a", "QC.Brokerage.Binance.BiNAnce")])
def test_finds_module_case_insensitive_name(id: str, display: str, search_name: str) -> None:
    create_fake_lean_cli_directory()

    module = JsonModule({"id": id, "configurations": [], "display-id": display},
                        MODULE_BROKERAGE, MODULE_CLI_PLATFORM)
    result = find_module(search_name, [module], MagicMock())
    assert result == module


@pytest.mark.parametrize("searching,expected", [("ads", False),
                                                ("BinanceFuturesBrokerage", True)])
def test_is_value_in_config(searching: str, expected: bool) -> None:
    module = JsonModule({"id": "asd", "configurations": [
        {
            "id": "live-mode-brokerage",
            "type": "info",
            "value": "BinanceFuturesBrokerage"
        }
    ], "display-id": "OUS"}, MODULE_BROKERAGE, MODULE_CLI_PLATFORM)

    result = module.is_value_in_config(searching)

    assert expected == result
