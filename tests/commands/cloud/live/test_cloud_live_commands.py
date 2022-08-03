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
from click.testing import CliRunner
from dependency_injector import providers
import lean.models.brokerages.local
from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory

def test_cloud_live_stop() -> None:
    create_fake_lean_cli_directory()

    api_client = mock.Mock()
    container.api_client.override(providers.Object(api_client))

    cloud_project_manager = mock.Mock()
    container.cloud_project_manager.override(providers.Object(cloud_project_manager))

    result = CliRunner().invoke(lean, ["cloud", "live", "stop", "Python Project"])

    assert result.exit_code == 0

def test_cloud_live_liquidate() -> None:
    create_fake_lean_cli_directory()

    api_client = mock.Mock()
    container.api_client.override(providers.Object(api_client))

    cloud_project_manager = mock.Mock()
    container.cloud_project_manager.override(providers.Object(cloud_project_manager))

    result = CliRunner().invoke(lean, ["cloud", "live", "liquidate", "Python Project"])

    assert result.exit_code == 0