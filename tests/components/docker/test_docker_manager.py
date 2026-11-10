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

from lean.components.docker.docker_manager import DockerManager
from lean.models.docker import DockerImage


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


def _run_image_and_capture_signal_handlers(docker_manager: DockerManager, container: mock.Mock) -> dict:
    handlers = {}

    docker_client = mock.Mock()
    docker_client.containers.run.return_value = container

    with mock.patch.object(docker_manager, "image_installed", return_value=True), \
            mock.patch.object(docker_manager, "create_network"), \
            mock.patch.object(docker_manager, "_get_docker_client", return_value=docker_client), \
            mock.patch("signal.signal", side_effect=lambda sig, handler: handlers.__setitem__(sig, handler)), \
            mock.patch("sys.exit"):
        docker_manager.run_image(DockerImage(name="quantconnect/lean", tag="latest"))

    return handlers


def test_run_image_stops_the_container_when_the_cli_is_terminated() -> None:
    import signal
    from time import sleep, time

    docker_manager = _create_docker_manager()

    container = mock.Mock()
    container.status = "exited"
    container.attrs = {"State": {"ExitCode": 0}}

    handlers = _run_image_and_capture_signal_handlers(docker_manager, container)

    stop_signals = [signal.SIGINT, signal.SIGTERM] + ([signal.SIGHUP] if hasattr(signal, "SIGHUP") else [])
    for stop_signal in stop_signals:
        assert stop_signal in handlers

    # A terminated CLI must stop the container exactly like Ctrl+C does
    handlers[signal.SIGTERM](signal.SIGTERM, None)

    deadline = time() + 5
    while not container.kill.called and time() < deadline:
        sleep(0.01)

    container.kill.assert_called_once()
