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

from lean.components.util.organization_manager import OrganizationManager


def _create_organization_manager(lean_config_manager: mock.Mock = mock.Mock()) -> OrganizationManager:
    logger = mock.Mock()
    return OrganizationManager(logger, lean_config_manager)


def test_organization_manager_gets_organization_id_from_lean_config() -> None:
    organization_id = "abc123"
    lean_config = {'organization-id': organization_id}

    lean_config_manager = mock.Mock()
    lean_config_manager.get_lean_config = mock.MagicMock(return_value=lean_config)

    organization_manager = _create_organization_manager(lean_config_manager=lean_config_manager)

    assert organization_manager.get_working_organization_id() == organization_id
    lean_config_manager.get_lean_config.assert_called()


def test_try_get_id_aborts_if_organization_id_is_not_in_the_lean_config() -> None:
    lean_config_manager = mock.Mock()
    lean_config_manager.get_lean_config = mock.MagicMock(return_value={})

    organization_manager = _create_organization_manager(lean_config_manager=lean_config_manager)

    with pytest.raises(RuntimeError):
        organization_manager.try_get_working_organization_id()


def test_organization_manager_sets_working_organization_id_in_lean_config():
    organization_id = "abc123"

    lean_config_manager = mock.Mock()
    lean_config_manager.set_properties = mock.Mock()

    organization_manager = _create_organization_manager(lean_config_manager=lean_config_manager)

    organization_manager.configure_working_organization_id(organization_id)

    lean_config_manager.set_properties.assert_called_with({"job-organization-id": organization_id})
    lean_config_manager.set_properties.assert_called_with({"organization-id": organization_id})
