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

import os
from pathlib import Path

import certifi
import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from responses import RequestsMock

from lean.container import container


# conftest.py is ran by pytest before loading each testing module
# Fixtures defined in here are therefore available in all testing modules


@pytest.fixture(autouse=True)
def fake_filesystem(fs: FakeFilesystem) -> FakeFilesystem:
    """A pytest fixture which mocks the filesystem before each test."""
    # The "fs" argument triggers pyfakefs' own pytest fixture to register
    # After pyfakefs has started all filesystem actions will happen on a fake in-memory filesystem

    # Proxy access to certifi's certificate authority bundle to the real filesystem
    # This is required to be able to send HTTP requests using requests
    fs.add_real_file(certifi.where())

    # Create a fake home directory and set the cwd to an empty directory
    fs.create_dir(Path.home() / "testing")
    os.chdir(Path.home() / "testing")

    # Reset all singletons so Path instances get recreated
    # Path instances are bound to the filesystem that was active at the time of their creation
    # When the filesystem changes, old Path instances bound to previous filesystems may cause weird behavior
    container.reset_singletons()

    return fs


@pytest.fixture(autouse=True)
def requests_mock() -> RequestsMock:
    """A pytest fixture which mocks the requests library before each test.

    If a test makes an HTTP request which hasn't been mocked, the request will fail.
    """
    with RequestsMock() as mock:
        yield mock


@pytest.fixture(autouse=True)
def reset_container_overrides() -> None:
    """A pytest fixture which makes sure all container and provider overrides are reset before each test."""
    for provider in container.traverse():
        provider.reset_override()

    container.reset_override()
