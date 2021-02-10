import os
import site
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from responses import RequestsMock

from lean.container import container
from tests.test_helpers import MockContainer, MockedContainer


# conftest.py is ran by pytest before loading each testing module
# Fixtures defined in here are therefore available in all testing modules


@pytest.fixture(autouse=True)
def mock_filesystem(fs: FakeFilesystem) -> FakeFilesystem:
    """A pytest fixture which mocks the filesystem before each test."""
    # The "fs" argument triggers pyfakefs' own pytest fixture to register
    # After pyfakefs has started all filesystem actions will happen on a fake in-memory filesystem

    # Simulate a fake home directory and set the cwd to an empty directory
    fs.create_dir(Path.home() / "testing")
    os.chdir(Path.home() / "testing")

    # Proxy access to site-packages to the real filesystem
    for path in site.getsitepackages():
        if Path(path).exists():
            fs.add_real_directory(path)

    # Make sure the container uses fresh singletons so Path instances are recreated
    container.reset_singletons()

    return fs


@pytest.fixture(autouse=True)
def requests_mock() -> RequestsMock:
    """A pytest fixture which mocks the requests library before each test.

    If a test makes an HTTP request which hasn't been mocked, the request will fail.
    """
    with RequestsMock() as mock:
        yield mock


@pytest.fixture()
def mock_container() -> MockContainer:
    """A pytest fixture which overrides the container with a MockContainer instance."""
    mocked_container = MockedContainer()
    container.override(mocked_container)

    yield MockContainer

    container.reset_override()

    # Reset all mocks
    for name, value in vars(MockContainer).items():
        if "_mock" in name:
            value.reset_mock()
