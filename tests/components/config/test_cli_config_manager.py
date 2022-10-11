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

import tempfile
from pathlib import Path

import pytest

from lean.components.config.cli_config_manager import CLIConfigManager
from lean.components.config.storage import Storage
from lean.constants import DEFAULT_ENGINE_IMAGE, DEFAULT_RESEARCH_IMAGE
from lean.models.docker import DockerImage


def create_storage() -> Storage:
    return Storage(str(Path(tempfile.mkdtemp()) / "storage"))


def test_get_option_by_key_returns_option_with_matching_key() -> None:
    cli_config_manager = CLIConfigManager(create_storage(), create_storage())

    for key in ["user-id", "api-token", "default-language"]:
        assert cli_config_manager.get_option_by_key(key).key == key


def test_get_option_by_key_raises_error_when_no_option_with_matching_key_exists() -> None:
    cli_config_manager = CLIConfigManager(create_storage(), create_storage())

    with pytest.raises(Exception):
        cli_config_manager.get_option_by_key("this-option-does-not-exist")


def test_get_engine_image_returns_default_image_when_nothing_configured() -> None:
    cli_config_manager = CLIConfigManager(create_storage(), create_storage())

    assert cli_config_manager.get_engine_image() == DockerImage.parse(DEFAULT_ENGINE_IMAGE)


def test_get_engine_image_returns_image_configured_via_option() -> None:
    cli_config_manager = CLIConfigManager(create_storage(), create_storage())
    cli_config_manager.engine_image.set_value("custom/lean:3")

    assert cli_config_manager.get_engine_image() == DockerImage(name="custom/lean", tag="3")


def test_get_engine_image_returns_override_when_given() -> None:
    cli_config_manager = CLIConfigManager(create_storage(), create_storage())
    cli_config_manager.engine_image.set_value("custom/lean:3")

    assert cli_config_manager.get_engine_image("custom/lean:5") == DockerImage(name="custom/lean", tag="5")


def test_get_research_image_returns_default_image_when_nothing_configured() -> None:
    cli_config_manager = CLIConfigManager(create_storage(), create_storage())

    assert cli_config_manager.get_research_image() == DockerImage.parse(DEFAULT_RESEARCH_IMAGE)


def test_get_research_image_returns_image_configured_via_option() -> None:
    cli_config_manager = CLIConfigManager(create_storage(), create_storage())
    cli_config_manager.research_image.set_value("custom/research:3")

    assert cli_config_manager.get_research_image() == DockerImage(name="custom/research", tag="3")


def test_get_research_image_returns_override_when_given() -> None:
    cli_config_manager = CLIConfigManager(create_storage(), create_storage())
    cli_config_manager.research_image.set_value("custom/research:3")

    assert cli_config_manager.get_research_image("custom/research:5") == DockerImage(name="custom/research", tag="5")
