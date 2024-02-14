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
import lean.models.brokerages.local
from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory

symbol_options = ["--ticker", "aapl", "--market", "usa", "--security-type", "equity"]

def test_local_live_add_security() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "add-security", "Python Project",
                                        *symbol_options])

    assert result.exit_code == 0


def test_local_live_add_security_fails_without_symbol_arguments() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "add-security", "Python Project"])

    assert result.exit_code != 0


def test_local_live_cancel_order() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "cancel-order", "Python Project",
                                            "--order-id", "1"])

    assert result.exit_code == 0


def test_local_live_cancel_order_fails_without_order_id() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "cancel-order", "Python Project"])

    assert result.exit_code != 0


def test_local_live_liquidate_all_symbols() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "liquidate", "Python Project"])

    assert result.exit_code == 0


def test_local_live_liquidate_one_symbol() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "liquidate", "Python Project",
                                        *symbol_options])

    assert result.exit_code == 0


def test_local_live_stop() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "stop", "Python Project"])

    assert result.exit_code == 0


def test_local_live_submit_order() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "submit-order", "Python Project",
                                        "--order-type", "market", "--quantity", 10,
                                        *symbol_options])

    assert result.exit_code == 0


def test_local_live_submit_order_fails_without_order_type_and_quantity() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "submit-order", "Python Project",
                                        *symbol_options])

    assert result.exit_code != 0


def test_local_live_update_order() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "update-order", "Python Project",
                                            "--order-id", "1"])

    assert result.exit_code == 0

def test_local_live_update_order_fails_without_order_id() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "update-order", "Python Project"])

    assert result.exit_code != 0

def test_local() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = mock.MagicMock()
    project_config_manager.get_latest_live_directory.return_value = "mock_live_dir"
    container.project_config_manager = project_config_manager

    output_config_manager = mock.Mock()
    container.output_config_manager = output_config_manager

    docker_manager = mock.MagicMock()
    docker_manager.read_from_file.return_value = {"success": True}
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["live", "add-security", "Python Project",
                                        *symbol_options])

    assert result.exit_code == 0