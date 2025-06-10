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

from lean.components.util.temp_manager import TempManager
from unittest import mock


def test_create_temporary_directory_creates_empty_directory() -> None:
    temp_manager = TempManager(mock.Mock())

    path = temp_manager.create_temporary_directory()

    assert path.is_dir()
    assert next(path.iterdir(), None) is None


def test_create_temporary_directory_creates_new_directory_every_time() -> None:
    temp_manager = TempManager(mock.Mock())

    assert temp_manager.create_temporary_directory() != temp_manager.create_temporary_directory()


def test_delete_temporary_directories_deletes_all_previously_created_directories() -> None:
    temp_manager = TempManager(mock.Mock())

    paths = []
    for i in range(5):
        paths.append(temp_manager.create_temporary_directory())

    for path in paths:
        assert path.is_dir()

    temp_manager.delete_temporary_directories()

    for path in paths:
        assert not path.is_dir()
