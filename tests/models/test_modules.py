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

import runpy
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from requests.exceptions import ConnectionError as RequestsConnectionError
from responses import RequestsMock

import lean.models
from lean.models.modules import NuGetPackage


def _write_modules_json_placeholder(fs: FakeFilesystem) -> None:
    fs.add_real_file(lean.models.__file__)
    fs.create_file(lean.models.file_path)


def test_modules_json_placeholder_is_replaced_by_the_downloaded_file(fs: FakeFilesystem,
                                                                      requests_mock: RequestsMock) -> None:
    _write_modules_json_placeholder(fs)
    modules = {"SomeModule": {"version": "1.0"}}
    requests_mock.add(requests_mock.GET, lean.models.url, json={"modules": modules})

    module_globals = runpy.run_path(lean.models.__file__)

    assert module_globals["json_modules"] == modules
    assert Path(lean.models.file_path).stat().st_size > 0


def test_modules_json_placeholder_raises_not_found_when_download_fails(fs: FakeFilesystem,
                                                                        requests_mock: RequestsMock) -> None:
    _write_modules_json_placeholder(fs)
    requests_mock.add(requests_mock.GET, lean.models.url, body=RequestsConnectionError())

    with pytest.raises(FileNotFoundError, match="Modules json not found"):
        runpy.run_path(lean.models.__file__)


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
