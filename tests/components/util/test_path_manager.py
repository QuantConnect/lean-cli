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

import platform
from pathlib import Path

import pytest

from lean.components.util.path_manager import PathManager
from lean.components.util.platform_manager import PlatformManager


@pytest.fixture(autouse=True)
def fake_filesystem() -> None:
    """A pytest fixture which overrides the filesystem mock so that the tests in this file run on a real filesystem."""
    return None


def test_get_relative_path_returns_relative_path_when_destination_is_relative_to_source() -> None:
    path_manager = PathManager(PlatformManager())

    source = Path.cwd()
    destination = Path.cwd() / "path" / "to" / "file.txt"

    assert path_manager.get_relative_path(destination, source) == Path("path") / "to" / "file.txt"


def test_get_relative_path_returns_full_destination_path_when_destination_is_not_relative_to_source() -> None:
    path_manager = PathManager(PlatformManager())

    source = Path.cwd()
    destination = Path.cwd().parent

    assert path_manager.get_relative_path(destination, source) == destination


def test_get_relative_path_uses_cwd_as_source_when_not_given() -> None:
    path_manager = PathManager(PlatformManager())

    assert path_manager.get_relative_path(Path.cwd() / "path" / "to" / "file.txt") == Path("path/to/file.txt")


def test_is_path_valid_returns_true_for_valid_path() -> None:
    path_manager = PathManager(PlatformManager())

    assert path_manager.is_path_valid(Path("My Path/file.txt"))


@pytest.mark.parametrize("path,valid", [("My Path/file.txt", True),
                                        ("My > Path/file.txt", False),
                                        ("My < Path/file.txt", False),
                                        ("My : Path/file.txt", False),
                                        ("My \" Path/file.txt", False),
                                        ("My | Path/file.txt", False),
                                        ("My ? Path/file.txt", False),
                                        ("My * Path/file.txt", False),
                                        ("CON/file.txt", False),
                                        ("PRN/file.txt", False),
                                        ("AUX/file.txt", False),
                                        ("NUL/file.txt", False),
                                        ("COM1/file.txt", False),
                                        ("COM2/file.txt", False),
                                        ("COM3/file.txt", False),
                                        ("COM4/file.txt", False),
                                        ("COM5/file.txt", False),
                                        ("COM6/file.txt", False),
                                        ("COM7/file.txt", False),
                                        ("COM8/file.txt", False),
                                        ("COM9/file.txt", False),
                                        ("LPT1/file.txt", False),
                                        ("LPT2/file.txt", False),
                                        ("LPT3/file.txt", False),
                                        ("LPT4/file.txt", False),
                                        ("LPT5/file.txt", False),
                                        ("LPT6/file.txt", False),
                                        ("LPT7/file.txt", False),
                                        ("LPT8/file.txt", False),
                                        ("LPT9/file.txt", False),
                                        ("My Path /file.txt", False),
                                        ("My Path./file.txt", False),
                                        (" My Path/file.txt", False),
                                        ("My Path/CON.txt", False),
                                        ("My Path/CON.tmp.txt", False)])
def test_is_path_valid_windows(path: str, valid: bool) -> None:
    if platform.system() != "Windows":
        pytest.skip("This test requires Windows")

    path_manager = PathManager(PlatformManager())

    assert path_manager.is_path_valid(Path(path)) == valid


@pytest.mark.parametrize("name, valid", [("123", True),
                                         ("abc", True),
                                         ("1a2b3c", True),
                                         ("a-1_b-2", True),
                                         ("/1-a/2_b 3 c/xyz", True),
                                         ("1 a/2_b/3-c", True),
                                         ("1a2b3c$", False),
                                         ("abc:123", False),
                                         ("abc.def", False)])
def test_is_name_valid(name: str, valid: bool) -> None:
    path_manager = PathManager(PlatformManager())

    assert path_manager.is_name_valid(name) == valid
