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

import pytest

from lean.models.docker import DockerImage


@pytest.mark.parametrize("value,name,tag", [("lean", "lean", "latest"),
                                            ("lean:latest", "lean", "latest"),
                                            ("lean:123", "lean", "123"),
                                            ("quantconnect/lean", "quantconnect/lean", "latest"),
                                            ("quantconnect/lean:latest", "quantconnect/lean", "latest"),
                                            ("quantconnect/lean:123", "quantconnect/lean", "123")])
def test_docker_image_name_parse_parses_value(value: str, name: str, tag: str) -> None:
    result = DockerImage.parse(value)

    assert result.name == name
    assert result.tag == tag


def test_docker_image_str_returns_full_name() -> None:
    assert str(DockerImage(name="quantconnect/lean", tag="latest")) == "quantconnect/lean:latest"
