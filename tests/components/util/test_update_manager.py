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

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple
from unittest import mock

import pytest
from docker.errors import APIError
from responses import RequestsMock

import lean
from lean.components.config.storage import Storage
from lean.components.util.http_client import HTTPClient
from lean.components.util.update_manager import UpdateManager
from lean.models.docker import DockerImage

DOCKER_IMAGE = DockerImage(name="quantconnect/lean", tag="latest")


def create_objects() -> Tuple[mock.Mock, Storage, mock.Mock, UpdateManager]:
    logger = mock.Mock()
    storage = Storage(str(Path("~/.lean/cache").expanduser()))
    docker_manager = mock.Mock()

    update_manager = UpdateManager(logger, HTTPClient(logger), storage, docker_manager)

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
@pytest.mark.parametrize("hours", [23, 24])
def test_warn_if_cli_outdated_always_checks_when_force_is_true(requests_mock: RequestsMock, hours: int) -> None:
    requests_mock.add(requests_mock.GET, "https://pypi.org/pypi/lean/json", '{ "info": { "version": "0.0.2" } }')

    logger, storage, docker_manager, update_manager = create_objects()
    storage.set("last-update-check-cli", (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).timestamp())

    update_manager.warn_if_cli_outdated(force=True)

    logger.warn.assert_called()


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


def test_pull_docker_image_if_necessary_pulls_when_docker_hub_has_newer_version() -> None:
    logger, storage, docker_manager, update_manager = create_objects()

    docker_manager.image_installed.return_value = True
    docker_manager.get_local_digest.return_value = "abc"
    docker_manager.get_remote_digest.return_value = "def"

    update_manager.pull_docker_image_if_necessary(DOCKER_IMAGE, False)

    docker_manager.pull_image.assert_called_once_with(DOCKER_IMAGE)


def test_pull_docker_image_if_necessary_pulls_when_image_is_not_installed() -> None:
    logger, storage, docker_manager, update_manager = create_objects()

    docker_manager.image_installed.return_value = False
    docker_manager.get_local_digest.return_value = "abc"

    update_manager.pull_docker_image_if_necessary(DOCKER_IMAGE, False)

    docker_manager.pull_image.assert_called_once_with(DOCKER_IMAGE)


@pytest.mark.parametrize("hours,update_warning_expected", [(24 * 6, False), (24 * 7, True)])
def test_pull_docker_image_if_necessary_only_pulls_once_every_week(hours: int, update_warning_expected: bool) -> None:
    logger, storage, docker_manager, update_manager = create_objects()

    storage.set(f"last-update-check-{DOCKER_IMAGE}",
                (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).timestamp())

    docker_manager.image_installed.return_value = True
    docker_manager.get_local_digest.return_value = "abc"
    docker_manager.get_remote_digest.return_value = "def"

    update_manager.pull_docker_image_if_necessary(DOCKER_IMAGE, False)

    if update_warning_expected:
        docker_manager.pull_image.assert_called_once_with(DOCKER_IMAGE)
    else:
        docker_manager.pull_image.assert_not_called()


def test_pull_docker_image_if_necessary_forces_pull_when_force_true() -> None:
    logger, storage, docker_manager, update_manager = create_objects()

    storage.set(f"last-update-check-{DOCKER_IMAGE}", datetime.now(tz=timezone.utc).timestamp())

    docker_manager.image_installed.return_value = True
    docker_manager.get_local_digest.return_value = "abc"
    docker_manager.get_remote_digest.return_value = "def"

    update_manager.pull_docker_image_if_necessary(DOCKER_IMAGE, True)

    docker_manager.pull_image.assert_called_once_with(DOCKER_IMAGE)


def test_pull_docker_image_if_necessary_does_nothing_when_api_responds_with_error() -> None:
    logger, storage, docker_manager, update_manager = create_objects()

    def get_remote_digest(image: DockerImage) -> str:
        raise APIError("oops")

    docker_manager.image_installed.return_value = True
    docker_manager.get_local_digest.return_value = "abc"
    docker_manager.get_remote_digest.side_effect = get_remote_digest

    update_manager.pull_docker_image_if_necessary(DOCKER_IMAGE, False)

    docker_manager.pull_image.assert_not_called()


def test_show_announcements_logs_when_announcements_have_never_been_shown(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://raw.githubusercontent.com/QuantConnect/lean-cli/master/announcements.json",
                      json.dumps({
                          "announcements": [
                              {
                                  "date": "2021-06-04",
                                  "message": "Downloading data for local usage is now a lot easier:\nhttps://www.lean.io/docs/lean-cli/datasets/local-data"
                              }
                          ]
                      }))

    logger, storage, docker_manager, update_manager = create_objects()

    update_manager.show_announcements()

    logger.info.assert_called()


def test_show_announcements_logs_when_announcements_have_been_updated(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://raw.githubusercontent.com/QuantConnect/lean-cli/master/announcements.json",
                      json.dumps({
                          "announcements": [
                              {
                                  "date": "2021-06-04",
                                  "message": "Downloading data for local usage is now a lot easier:\nhttps://www.lean.io/docs/lean-cli/datasets/local-data"
                              }
                          ]
                      }))

    logger, storage, docker_manager, update_manager = create_objects()

    storage.set("last-announcements-hash", "abc")

    update_manager.show_announcements()

    logger.info.assert_called()


@pytest.mark.parametrize("hours,update_warning_expected", [(23, False), (24, True)])
def test_show_announcements_only_checks_once_every_day(requests_mock: RequestsMock,
                                                       hours: int,
                                                       update_warning_expected: bool) -> None:
    if update_warning_expected:
        requests_mock.add(requests_mock.GET,
                          "https://raw.githubusercontent.com/QuantConnect/lean-cli/master/announcements.json",
                          json.dumps({
                              "announcements": [
                                  {
                                      "date": "2021-06-04",
                                      "message": "Downloading data for local usage is now a lot easier:\nhttps://www.lean.io/docs/lean-cli/datasets/local-data"
                                  }
                              ]
                          }))

    logger, storage, docker_manager, update_manager = create_objects()
    storage.set("last-update-check-announcements", (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).timestamp())

    update_manager.show_announcements()

    if update_warning_expected:
        logger.info.assert_called()
    else:
        logger.info.assert_not_called()


def test_show_announcements_does_nothing_when_latest_announcements_shown_before(requests_mock: RequestsMock) -> None:
    announcements_json = json.dumps({
        "announcements": [
            {
                "date": "2021-06-04",
                "message": "Downloading data for local usage is now a lot easier:\nhttps://www.lean.io/docs/lean-cli/datasets/local-data"
            }
        ]
    })

    requests_mock.add(requests_mock.GET,
                      "https://raw.githubusercontent.com/QuantConnect/lean-cli/master/announcements.json",
                      announcements_json)

    logger, storage, docker_manager, update_manager = create_objects()

    storage.set("last-announcements-hash", hashlib.md5(announcements_json.encode("utf-8")).hexdigest())

    update_manager.show_announcements()

    logger.info.assert_not_called()


def test_show_announcements_does_nothing_when_there_are_no_announcements(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://raw.githubusercontent.com/QuantConnect/lean-cli/master/announcements.json",
                      json.dumps({
                          "announcements": []
                      }))

    logger, storage, docker_manager, update_manager = create_objects()

    update_manager.show_announcements()

    logger.info.assert_not_called()


def test_show_announcement_does_nothing_when_github_responds_with_error(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://raw.githubusercontent.com/QuantConnect/lean-cli/master/announcements.json",
                      "",
                      status=500)

    logger, storage, docker_manager, update_manager = create_objects()

    update_manager.show_announcements()

    logger.info.assert_not_called()
