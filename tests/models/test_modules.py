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

from lean.models.modules import NuGetPackage


def test_get_file_name_returns_correct_value() -> None:
    package = NuGetPackage(name="QuantConnect.Lean", version="2.5.11940")

    assert package.get_file_name() == "QuantConnect.Lean.2.5.11940.nupkg"


def test_parse_returns_correct_value() -> None:
    package = NuGetPackage.parse("QuantConnect.Lean.2.5.11940.nupkg")

    assert package.name == "QuantConnect.Lean"
    assert package.version == "2.5.11940"


def test_get_file_name_parse_round_trip() -> None:
    file_name = "QuantConnect.Lean.2.5.11940.nupkg"

    assert NuGetPackage.parse(file_name).get_file_name() == file_name
