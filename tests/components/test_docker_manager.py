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

from responses import RequestsMock

from lean.components.docker_manager import DockerManager


def test_tag_exists_returns_true_when_tag_exists_in_registry(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://registry.hub.docker.com/v1/repositories/quantconnect/lean/tags",
                      '[{ "layer": "", "name": "122" }, { "layer": "", "name": "123" }]')

    docker_manager = DockerManager(mock.Mock())

    assert docker_manager.tag_exists("quantconnect/lean", "123")


def test_tag_exists_returns_false_when_tag_does_not_exist_in_registry(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET,
                      "https://registry.hub.docker.com/v1/repositories/quantconnect/lean/tags",
                      '[{ "layer": "", "name": "122" }, { "layer": "", "name": "124" }]')

    docker_manager = DockerManager(mock.Mock())

    assert not docker_manager.tag_exists("quantconnect/lean", "123")
