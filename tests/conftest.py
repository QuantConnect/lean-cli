import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from lean.constants import GLOBAL_CONFIG_DIR


# conftest.py is ran by pytest before loading each testing module
# We use it to make sure the filesystem is mocked before running each test
# This is done because a lot of functionality in the CLI works with the filesystem

@pytest.fixture(autouse=True)
def mock_filesystem(fs: FakeFilesystem) -> FakeFilesystem:
    """Mock the filesystem before each test."""
    # The "fs" argument triggers pyfakefs' own pytest fixture to register
    # After pyfakefs has started all filesystem actions will happen on a fake in-memory filesystem

    # Make sure the global config directory is accessible
    global_config_dir = Path.home() / GLOBAL_CONFIG_DIR
    if not global_config_dir.exists():
        global_config_dir.mkdir(parents=True)

    # Set the current working directory to an empty directory
    test_dir = Path.home() / "testing"
    test_dir.mkdir()
    os.chdir(test_dir)

    return fs
