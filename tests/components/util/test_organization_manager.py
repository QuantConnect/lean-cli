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

import click
import pytest

from lean.components.util.organization_manager import OrganizationManager
from lean.models.api import QCMinimalOrganization


def _create_organization_manager(api_client: mock.Mock = mock.Mock(),
                                 lean_config_manager: mock.Mock = mock.Mock()) -> OrganizationManager:
    logger = mock.Mock()
    return OrganizationManager(logger, api_client, lean_config_manager)


@pytest.mark.parametrize("use_lean_config_manager", [True, False])
def test_organization_manager_gets_organization_id_from_lean_config(use_lean_config_manager: bool) -> None:
    organization_id = "abc123"
    lean_config = {'organization-id': organization_id}

    lean_config_manager = mock.Mock()
    lean_config_manager.get_lean_config = mock.MagicMock(return_value=lean_config)

    organization_manager = _create_organization_manager(lean_config_manager=lean_config_manager)

    if use_lean_config_manager:
        lean_config = None

    assert organization_manager.get_working_organization_id(lean_config) == organization_id

    if use_lean_config_manager:
        lean_config_manager.get_lean_config.assert_called()
    else:
        lean_config_manager.get_lean_config.assert_not_called()


@pytest.mark.parametrize("proceed", [True, False])
def test_organization_manager_prompts_user_if_lean_config_does_not_have_the_organization_id(proceed: bool) -> None:
    api_client = mock.Mock()
    api_client.organizations.get_all = mock.MagicMock(return_value=[
        QCMinimalOrganization(id="abc", name="abc", type="type", ownerName="You", members=1, preferred=True)
    ])

    lean_config_manager = mock.Mock()
    lean_config_manager.get_lean_config = mock.MagicMock(return_value={})

    organization_manager = _create_organization_manager(api_client=api_client, lean_config_manager=lean_config_manager)

    def get_organization_id():
        return organization_manager.get_working_organization_id()

    with mock.patch('click.confirm', return_value=proceed) as mock_click_confirm:
        if proceed:
            assert get_organization_id() == "abc"
        else:
            with pytest.raises(click.Abort):
                get_organization_id()

    mock_click_confirm.assert_called_once()
    assert "continue?" in mock_click_confirm.call_args.args[0]


def test_organization_manager_sets_working_organization_to_given_config():
    organization_id = "abc123"
    lean_config = {}

    lean_config_manager = mock.Mock()
    lean_config_manager.set_properties = mock.Mock()

    organization_manager = _create_organization_manager(lean_config_manager=lean_config_manager)

    organization_manager.configure_working_organization_id(organization_id, lean_config)

    assert "organization-id" in lean_config and lean_config["organization-id"] == organization_id
    lean_config_manager.set_properties.assert_not_called()


def test_organization_manager_sets_working_organization_using_lean_config_manager():
    organization_id = "abc123"
    lean_config_updates = {"organization-id": organization_id}

    lean_config_manager = mock.Mock()
    lean_config_manager.set_properties = mock.Mock()

    organization_manager = _create_organization_manager(lean_config_manager=lean_config_manager)

    organization_manager.configure_working_organization_id(organization_id)

    lean_config_manager.set_properties.assert_called_once_with(lean_config_updates)
