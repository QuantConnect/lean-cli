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

from lean.components.util.path_validator import PathValidator


@pytest.fixture(autouse=True)
def fake_filesystem() -> None:
    """A pytest fixture which overrides the filesystem mock so that the tests in this file run on a real filesystem."""
    return None


def test_is_path_valid_returns_true_for_valid_path() -> None:
    path_validator = PathValidator()

    assert path_validator.is_path_valid(Path.cwd() / "My Path/file.txt")


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

    path_validator = PathValidator()

    if valid:
        assert path_validator.is_path_valid(Path.cwd() / path)
    else:
        assert not path_validator.is_path_valid(Path.cwd() / path)
