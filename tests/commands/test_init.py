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
import zipfile
from pathlib import Path
from typing import List
from unittest import mock

import pytest
from click.testing import CliRunner
from responses import RequestsMock

from lean.commands import lean
from lean.components.util.logger import Logger
from lean.components.util.organization_manager import OrganizationManager
from lean.container import container
from lean.models.api import QCMinimalOrganization


@pytest.fixture(autouse=True)
def create_fake_archive(requests_mock: RequestsMock) -> None:
    archive_path = Path(tempfile.mkdtemp()) / "archive.zip"

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("Lean-master/Data/equity/readme.md", "# This is just a test")
        archive.writestr("Lean-master/Launcher/config.json", """
{
  // this configuration file works by first loading all top-level
  // configuration items and then will load the specified environment
  // on top, this provides a layering affect. environment names can be
  // anything, and just require definition in this file. There's
  // two predefined environments, 'backtesting' and 'live', feel free
  // to add more!

  "environment": "backtesting", // "live-paper", "backtesting", "live-interactive", "live-interactive-iqfeed"

  // data documentation
  "data-folder": "data"
}
        """.strip())

    with open(archive_path, "rb") as archive:
        requests_mock.assert_all_requests_are_fired = False
        requests_mock.add(requests_mock.GET, "https://github.com/QuantConnect/Lean/archive/master.zip", archive.read())


@pytest.fixture(autouse=True, scope="function")
def set_unauthenticated() -> None:
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = False
    container.api_client = api_client


def _get_all_organizations() -> List[QCMinimalOrganization]:
    return [
        QCMinimalOrganization(id="abcd1234abcd1234abcd1234abcd1234", name="Organization1", type="type",
                              ownerName="You", members=1, preferred=True),
    ]


def _get_test_organization() -> QCMinimalOrganization:
    return _get_all_organizations()[0]


@pytest.fixture(autouse=True, scope="function")
def set_mock_organizations(set_unauthenticated) -> None:
    def mock_get_organization(org_id: str) -> QCMinimalOrganization:
        return next(iter(o for o in _get_all_organizations() if o.id == org_id), None)

    # container.api_client is already a mock from set_unauthenticated()
    api_client = container.api_client
    api_client.organizations.get_all.side_effect = _get_all_organizations
    api_client.organizations.get.side_effect = mock_get_organization


@pytest.fixture(autouse=True, scope="function")
def reset_organization_manager() -> None:
    container.organization_manager = OrganizationManager(mock.Mock(), container.lean_config_manager)


def test_init_aborts_when_config_file_already_exists() -> None:
    (Path.cwd() / "lean.json").touch()

    result = CliRunner().invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_aborts_when_data_directory_already_exists() -> None:
    (Path.cwd() / "data").mkdir()

    result = CliRunner().invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_prompts_for_confirmation_when_directory_not_empty() -> None:
    (Path.cwd() / "my-custom-file.txt").touch()

    result = CliRunner().invoke(lean, ["init"], input="n\n")

    assert result.exit_code != 0
    assert "continue?" in result.output


def test_init_prompts_for_default_language_when_not_set_yet() -> None:
    result = CliRunner().invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    assert container.cli_config_manager.default_language.get_value() == "csharp"


def test_init_creates_data_directory_from_repo() -> None:
    result = CliRunner().invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    readme_path = Path.cwd() / "data" / "equity" / "readme.md"
    assert readme_path.exists()

    with open(readme_path) as readme_file:
        assert readme_file.read() == "# This is just a test"


def test_init_creates_clean_config_file_from_repo() -> None:
    result = CliRunner().invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    config_path = Path.cwd() / "lean.json"
    assert config_path.exists()
    assert config_path.read_text(encoding="utf-8") == """
{{
    "data-folder": "data",
    "organization-id": "{0}"
}}
    """.format(_get_test_organization().id).strip()


def assert_organization_id_is_in_lean_config(organization_id: str) -> None:
    lean_config_manager = container.lean_config_manager
    config = lean_config_manager.get_lean_config()

    assert "organization-id" in config and config["organization-id"] == organization_id


def test_init_prompts_for_organization_if_option_not_passed() -> None:
    organization = _get_test_organization()

    with mock.patch.object(Logger, 'prompt_list', return_value=organization.id) as mock_prompt_list:
        result = CliRunner().invoke(lean, ["init"])

    assert result.exit_code == 0

    mock_prompt_list.assert_called_with("Select the organization to use for this Lean CLI instance", mock.ANY)
    assert_organization_id_is_in_lean_config(organization.id)


@pytest.mark.parametrize("use_name", [False, True])
def test_init_uses_organization_given_as_option(use_name: bool) -> None:
    organization = _get_test_organization()

    with mock.patch.object(Logger, 'prompt_list', return_value=None) as mock_prompt_list:
        result = CliRunner().invoke(lean,
                                    ["init", "--organization", organization.name if use_name else organization.id])

    assert result.exit_code == 0

    assert not any("Select the organization" in call.args[0] for call in mock_prompt_list.call_args_list)

    assert_organization_id_is_in_lean_config(organization.id)
