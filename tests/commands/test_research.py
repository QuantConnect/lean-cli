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

import json
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from lean.commands import lean
from lean.constants import DEFAULT_RESEARCH_IMAGE, LEAN_ROOT_PATH, LEAN_PYTHON_VERSION
from lean.container import container
from lean.models.docker import DockerImage
from tests.test_helpers import create_fake_lean_cli_directory

RESEARCH_IMAGE = DockerImage.parse(DEFAULT_RESEARCH_IMAGE)


def test_research_runs_research_container() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == RESEARCH_IMAGE


def test_research_mounts_lean_config_to_notebooks_directory_as_well() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    lean_config = next(m["Source"] for m in kwargs["mounts"] if m["Target"] == f"{LEAN_ROOT_PATH}/config.json")
    assert any(m["Source"] == lean_config and m["Target"] == f"{LEAN_ROOT_PATH}/Notebooks/config.json" for m in
               kwargs["mounts"])


def test_research_adds_credentials_to_project_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    container.cli_config_manager.user_id.set_value("123")
    container.cli_config_manager.api_token.set_value("456")

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = [m for m in kwargs["mounts"] if m["Target"] == f"{LEAN_ROOT_PATH}/Notebooks/config.json"][0]

    with open(mount["Source"]) as file:
        config = json.load(file)

    assert config["job-user-id"] == "123"
    assert config["api-access-token"] == "456"


def test_research_mounts_data_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert str(Path.cwd() / "data") in kwargs["volumes"]


def test_research_mounts_project_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert str(Path.cwd() / "Python Project") in kwargs["volumes"]


def test_research_exposes_8888_when_no_port_given() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["ports"] == {"8888": "8888"}


def test_research_exposes_custom_port_when_given() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project", "--port", "1234"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["ports"] == {"8888": "1234"}


@mock.patch("webbrowser.open")
def test_research_opens_browser_when_container_started(open) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    logs = f"""
[I 21:06:21.500 LabApp] Writing notebook server cookie secret to /root/.local/share/jupyter/runtime/notebook_cookie_secret
[W 21:06:21.692 LabApp] All authentication is disabled.  Anyone who can connect to this server will be able to run code.
[I 21:06:21.698 LabApp] JupyterLab extension loaded from /opt/miniconda3/lib/python{LEAN_PYTHON_VERSION}/site-packages/jupyterlab
[I 21:06:21.698 LabApp] JupyterLab application directory is /opt/miniconda3/share/jupyter/lab
[I 21:06:21.700 LabApp] Serving notebooks from local directory: /Lean/Launcher/bin/Debug/Notebooks
[I 21:06:21.700 LabApp] The Jupyter Notebook is running at:
[I 21:06:21.700 LabApp] http://290fd51da0b5:8888/
    """.strip()

    assert "on_output" in kwargs
    for line in logs.splitlines():
        kwargs["on_output"](line)

    open.assert_called_once_with("http://localhost:8888/")


def test_research_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(RESEARCH_IMAGE)
    docker_manager.run_image.assert_called_once()


def test_research_runs_custom_image_when_set_in_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    container.cli_config_manager.research_image.set_value("custom/research:123")

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/research", tag="123")


def test_research_runs_custom_image_when_given_as_option() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    container.cli_config_manager.research_image.set_value("custom/research:123")

    result = CliRunner().invoke(lean, ["research", "Python Project", "--image", "custom/research:456"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/research", tag="456")


def test_optimize_runs_lean_container_with_extra_docker_config() -> None:
    import docker.types

    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    container.initialize(docker_manager)

    result = CliRunner().invoke(lean, ["research", "Python Project",
                                       "--extra-docker-config",
                                       '{"device_requests": [{"count": -1, "capabilities": [["compute"]]}]}'])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == RESEARCH_IMAGE
    assert "device_requests" in kwargs
    assert kwargs["device_requests"] == [docker.types.DeviceRequest(count=-1, capabilities=[["compute"]])]
