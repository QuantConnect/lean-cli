import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from responses import RequestsMock

from lean.container import container


# conftest.py is ran by pytest before loading each testing module
# Fixtures defined in here are therefore available in all testing modules

@pytest.fixture(autouse=True)
def mock_filesystem(fs: FakeFilesystem) -> FakeFilesystem:
    """A pytest fixture which mocks the filesystem before each test."""
    # The "fs" argument triggers pyfakefs' own pytest fixture to register
    # After pyfakefs has started all filesystem actions will happen on a fake in-memory filesystem

    # Create a fake home directory and set the cwd to an empty directory
    fs.create_dir(Path.home() / "testing")
    os.chdir(Path.home() / "testing")

    # Reset singletons so that fresh Path instances get created
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
