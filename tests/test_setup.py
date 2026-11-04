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

import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from setuptools.dist import Distribution

import lean.models

REPOSITORY_ROOT = Path(__file__).parent.parent
MODULES_FILE = f"lean/{lean.models.file_name}"
DOWNLOADED_MODULES_JSON = '{"modules": {}}'
# Newer setuptools releases removed the --dry-run option
requires_dry_run = pytest.mark.skipif("dry-run" not in [option[0] for option in Distribution.global_options],
                                      reason="This setuptools version has no --dry-run option")


@pytest.fixture
def source_tree(fs: FakeFilesystem) -> Path:
    """A minimal real copy of the package sources holding a downloaded modules json, as a checkout has."""
    # setup.py runs in a subprocess, which needs the real filesystem
    fs.pause()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for relative_path in ["setup.py", "README.md", "lean/__init__.py", "lean/models/__init__.py"]:
            (root / relative_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPOSITORY_ROOT / relative_path, root / relative_path)
        (root / MODULES_FILE).write_text(DOWNLOADED_MODULES_JSON)
        yield root
    fs.resume()


def _run_setup(directory: Path, *arguments: str) -> None:
    subprocess.run([sys.executable, "setup.py", *arguments], cwd=directory, check=True, capture_output=True)


def _assert_wheel_has_empty_modules_placeholder(dist_directory: Path) -> None:
    with zipfile.ZipFile(next(dist_directory.glob("*.whl"))) as wheel:
        assert wheel.getinfo(MODULES_FILE).file_size == 0
        assert MODULES_FILE in wheel.read(next(name for name in wheel.namelist() if name.endswith("RECORD"))).decode()


def test_setup_metadata_keeps_downloaded_modules_json(source_tree: Path) -> None:
    _run_setup(source_tree, "--version")

    assert (source_tree / MODULES_FILE).read_text() == DOWNLOADED_MODULES_JSON


@pytest.mark.parametrize("arguments", [
    ["build_py", "--build-lib", "."],
    pytest.param(["--dry-run", "build_py", "--build-lib", "."], marks=requires_dry_run),
    pytest.param(["--dry-run", "build_py", "--build-lib", "build/lib"], marks=requires_dry_run)
])
def test_setup_in_place_and_dry_run_builds_keep_downloaded_modules_json(source_tree: Path, arguments: list) -> None:
    _run_setup(source_tree, *arguments)

    assert (source_tree / MODULES_FILE).read_text() == DOWNLOADED_MODULES_JSON


def test_setup_wheel_records_empty_modules_placeholder_and_keeps_downloaded_file(source_tree: Path) -> None:
    _run_setup(source_tree, "bdist_wheel")

    _assert_wheel_has_empty_modules_placeholder(source_tree / "dist")
    assert (source_tree / MODULES_FILE).read_text() == DOWNLOADED_MODULES_JSON


def test_setup_sdist_has_empty_modules_placeholder_and_keeps_downloaded_file(source_tree: Path) -> None:
    _run_setup(source_tree, "sdist")

    with tarfile.open(next((source_tree / "dist").glob("*.tar.gz"))) as sdist:
        assert next(member for member in sdist.getmembers() if member.name.endswith(MODULES_FILE)).size == 0
    assert (source_tree / MODULES_FILE).read_text() == DOWNLOADED_MODULES_JSON


def test_setup_wheel_built_from_sdist_records_empty_modules_placeholder(source_tree: Path) -> None:
    _run_setup(source_tree, "sdist")
    with tarfile.open(next((source_tree / "dist").glob("*.tar.gz"))) as sdist:
        sdist.extractall(source_tree / "extracted")
    sdist_tree = next((source_tree / "extracted").iterdir())

    _run_setup(sdist_tree, "bdist_wheel")

    _assert_wheel_has_empty_modules_placeholder(sdist_tree / "dist")
