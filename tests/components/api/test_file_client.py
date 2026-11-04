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

from typing import Optional
from unittest import mock

import pytest

from lean.components.api.file_client import FileClient


@pytest.mark.parametrize("method, args, endpoint, expected_parameters", [
    ("create", (1, "main.py", "content"), "files/create", {"projectId": 1, "name": "main.py", "content": "content"}),
    ("update", (1, "main.py", "content"), "files/update", {"projectId": 1, "name": "main.py", "content": "content"}),
    ("delete", (1, "main.py"), "files/delete", {"projectId": 1, "name": "main.py"})
])
@pytest.mark.parametrize("code_source_id", [None, "cli"])
def test_file_client_sends_code_source_id_only_when_given(method: str, args: tuple, endpoint: str,
                                                          expected_parameters: dict, code_source_id: Optional[str]) -> None:
    api_client = mock.Mock()

    getattr(FileClient(api_client), method)(*args, code_source_id=code_source_id)

    if code_source_id is not None:
        expected_parameters = {**expected_parameters, "codeSourceId": code_source_id}
    api_client.post.assert_called_once_with(endpoint, expected_parameters)
