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

import pytest

from tests.conftest import initialize_container


@pytest.fixture(autouse=True)
def fake_filesystem(tmp_path, monkeypatch) -> None:
    """Replaces the in-memory filesystem with a real temporary directory for the UI tests.

    pyfakefs switches to the real filesystem process-wide for short moments, so the threads Textual runs its
    workers in sometimes read the real disk instead of the fake one.
    """
    monkeypatch.chdir(tmp_path)
    initialize_container()
