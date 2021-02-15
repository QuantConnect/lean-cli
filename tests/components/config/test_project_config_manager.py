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

from pathlib import Path

from lean.components.config.project_config_manager import ProjectConfigManager
from tests.test_helpers import create_fake_lean_cli_project


def test_get_project_config_returns_storage_instance_of_correct_file() -> None:
    create_fake_lean_cli_project()

    project_config_manager = ProjectConfigManager("config.json")
    project_config = project_config_manager.get_project_config(Path.cwd() / "Python Project")

    assert project_config.file == Path.cwd() / "Python Project" / "config.json"
