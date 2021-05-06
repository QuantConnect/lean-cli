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

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple
from unittest import mock

import pytest
from responses import RequestsMock

import lean
from lean.components.config.storage import Storage
from lean.components.util.update_manager import UpdateManager
from lean.models.docker import DockerImage


def create_objects() -> Tuple[mock.Mock, Storage, mock.Mock, UpdateManager]:
    logger = mock.Mock()
    storage = Storage(str(Path("~/.lean/cache").expanduser()))
    docker_manager = mock.Mock()

    update_manager = UpdateManager(logger, storage, docker_manager)

    return logger, storage, docker_manager, update_manager


@mock.patch.object(lean, "__version__", "0.0.1")
def test_warn_if_cli_outdated_warns_when_pypi_version_newer_than_current_version(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET, "https://pypi.org/pypi/lean/json", '{ "info": { "version": "0.0.2" } }')

    logger, storage, docker_manager, update_manager = create_objects()

    update_manager.warn_if_cli_outdated()

    logger.warn.assert_called()


@mock.patch.object(lean, "__version__", "dev")
def test_warn_if_cli_outdated_does_nothing_when_running_dev_version(requests_mock: RequestsMock) -> None:
    logger, storage, docker_manager, update_manager = create_objects()

    update_manager.warn_if_cli_outdated()

    logger.warn.assert_not_called()


@mock.patch.object(lean, "__version__", "0.0.1")
@pytest.mark.parametrize("hours,update_warning_expected", [(23, False), (24, True)])
def test_warn_if_cli_outdated_only_checks_once_every_day(requests_mock: RequestsMock,
                                                         hours: int,
                                                         update_warning_expected: bool) -> None:
    if update_warning_expected:
        requests_mock.add(requests_mock.GET, "https://pypi.org/pypi/lean/json", '{ "info": { "version": "0.0.2" } }')

    logger, storage, docker_manager, update_manager = create_objects()
    storage.set("last-update-check-cli", (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).timestamp())

    update_manager.warn_if_cli_outdated()

    if update_warning_expected:
        logger.warn.assert_called()
    else:
        logger.warn.assert_not_called()


@mock.patch.object(lean, "__version__", "0.0.1")
def test_warn_if_cli_outdated_does_nothing_when_running_latest_version(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET, "https://pypi.org/pypi/lean/json", '{ "info": { "version": "0.0.1" } }')

    logger, storage, docker_manager, update_manager = create_objects()

    update_manager.warn_if_cli_outdated()

    logger.warn.assert_not_called()


@mock.patch.object(lean, "__version__", "0.0.1")
def test_warn_if_cli_outdated_does_nothing_when_pypi_responds_with_error(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET, "https://pypi.org/pypi/lean/json", "", status=500)

    logger, storage, docker_manager, update_manager = create_objects()

    update_manager.warn_if_cli_outdated()

    logger.warn.assert_not_called()


def test_warn_if_docker_image_outdated_warns_when_docker_hub_has_newer_version(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://registry.hub.docker.com/v2/repositories/quantconnect/lean/tags/latest",
                      '{ "images": [ { "digest": "abc" } ] }')

    logger, storage, docker_manager, update_manager = create_objects()

    docker_manager.tag_installed.return_value = True
    docker_manager.get_digest.return_value = "def"

    update_manager.warn_if_docker_image_outdated(DockerImage(name="quantconnect/lean", tag="latest"))

    logger.warn.assert_called()


def test_warn_if_docker_image_outdated_does_nothing_when_latest_tag_not_installed(requests_mock: RequestsMock) -> None:
    logger, storage, docker_manager, update_manager = create_objects()

    docker_manager.tag_installed.return_value = False
    docker_manager.get_digest.return_value = "def"

    update_manager.warn_if_docker_image_outdated(DockerImage(name="quantconnect/lean", tag="latest"))

    logger.warn.assert_not_called()


@pytest.mark.parametrize("hours,update_warning_expected", [(24 * 13, False), (24 * 14, True)])
def test_warn_if_docker_image_outdated_only_checks_once_every_two_weeks(requests_mock: RequestsMock,
                                                                        hours: int,
                                                                        update_warning_expected: bool) -> None:
    if update_warning_expected:
        requests_mock.add(requests_mock.GET,
                          "https://registry.hub.docker.com/v2/repositories/quantconnect/lean/tags/latest",
                          '{ "images": [ { "digest": "abc" } ] }')

    logger, storage, docker_manager, update_manager = create_objects()
    storage.set("last-update-check-my-image", (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).timestamp())

    docker_manager.tag_installed.return_value = True
    docker_manager.get_digest.return_value = "def"

    update_manager.warn_if_docker_image_outdated(DockerImage(name="quantconnect/lean", tag="latest"))

    if update_warning_expected:
        logger.warn.assert_called()
    else:
        logger.warn.assert_not_called()


def test_warn_if_docker_image_outdated_does_nothing_when_not_outdated(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://registry.hub.docker.com/v2/repositories/quantconnect/lean/tags/latest",
                      '{ "images": [ { "digest": "abc" } ] }')

    logger, storage, docker_manager, update_manager = create_objects()

    docker_manager.tag_installed.return_value = True
    docker_manager.get_digest.return_value = "abc"

    update_manager.warn_if_docker_image_outdated(DockerImage(name="quantconnect/lean", tag="latest"))

    logger.warn.assert_not_called()


def test_warn_if_docker_image_outdated_does_nothing_when_api_responds_with_error(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://registry.hub.docker.com/v2/repositories/quantconnect/lean/tags/latest",
                      "",
                      status=500)

    logger, storage, docker_manager, update_manager = create_objects()

    docker_manager.tag_installed.return_value = True
    docker_manager.get_digest.return_value = "abc"

    update_manager.warn_if_docker_image_outdated(DockerImage(name="quantconnect/lean", tag="latest"))

    logger.warn.assert_not_called()
