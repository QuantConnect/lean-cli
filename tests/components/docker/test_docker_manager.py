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
from unittest import mock

import docker
import pytest

from lean.components.docker.docker_manager import DockerManager


def _create_docker_manager() -> DockerManager:
    return DockerManager(mock.Mock(), mock.Mock(), mock.Mock())


def test_write_to_file_does_not_let_the_host_shell_expand_the_payload() -> None:
    docker_manager = _create_docker_manager()

    container = mock.Mock()
    container.status = "running"

    payload = {"$type": "QuantConnect.Orders.MarketOrder", "quantity": 100}

    with mock.patch.object(docker_manager, "get_container_by_name", return_value=container), \
            mock.patch("subprocess.run") as run_mock:
        docker_manager.write_to_file("my-container", Path("/tmp/command.json"), payload)

    run_mock.assert_called_once()
    args, kwargs = run_mock.call_args

    # The command must be passed as a list so the host shell never parses it
    command = args[0]
    assert isinstance(command, list)
    assert kwargs.get("shell", False) is False

    echo_command = command[-1]

    # $type must reach the container untouched (raw JSON: real double quotes, no backslash escaping)
    assert '"$type"' in echo_command
    assert "\\" not in echo_command


def _get_docker_client_with_env(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("DOCKER_CLIENT_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("DOCKER_CLIENT_TIMEOUT", value)

    docker_manager = _create_docker_manager()
    # docker is imported at the top of this file: the tests run on a fake filesystem, where importing it
    # inside the test would fail
    with mock.patch.object(docker, "from_env") as from_env_mock:
        from_env_mock.return_value.ping.return_value = True
        docker_manager._get_docker_client()

    return from_env_mock


def test_get_docker_client_uses_the_sdk_default_timeout_when_docker_client_timeout_is_not_set(monkeypatch) -> None:
    from_env_mock = _get_docker_client_with_env(monkeypatch, None)

    from_env_mock.assert_called_once_with()


def test_get_docker_client_uses_the_sdk_default_timeout_when_docker_client_timeout_is_empty(monkeypatch) -> None:
    from_env_mock = _get_docker_client_with_env(monkeypatch, " ")

    from_env_mock.assert_called_once_with()


def test_get_docker_client_passes_docker_client_timeout_to_the_docker_client(monkeypatch) -> None:
    from_env_mock = _get_docker_client_with_env(monkeypatch, "300")

    from_env_mock.assert_called_once_with(timeout=300)


@pytest.mark.parametrize("value", ["abc", "0", "-5", "1.5"])
def test_get_docker_client_raises_when_docker_client_timeout_is_invalid(monkeypatch, value: str) -> None:
    with pytest.raises(RuntimeError, match="DOCKER_CLIENT_TIMEOUT"):
        _get_docker_client_with_env(monkeypatch, value)
