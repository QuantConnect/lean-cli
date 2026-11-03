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

from unittest import mock

import pytest

from lean.components.api.object_store_client import ObjectStoreClient
from lean.models.errors import RequestFailedError


def test_exists_returns_true_when_the_properties_are_returned() -> None:
    api = mock.Mock()
    api.post.return_value = {"metadata": {"key": "model.v2.pkl"}}

    assert ObjectStoreClient(api).exists("model.v2.pkl", "abc")

    api.post.assert_called_once_with("object/properties", {"organizationId": "abc", "key": "model.v2.pkl"})


def test_exists_returns_false_when_the_object_is_not_found() -> None:
    api = mock.Mock()
    api.post.side_effect = RequestFailedError(mock.MagicMock(), "File not found")

    assert not ObjectStoreClient(api).exists("model.v2.pkl", "abc")


def test_exists_raises_any_other_failure() -> None:
    api = mock.Mock()
    api.post.side_effect = RequestFailedError(mock.MagicMock(), "Organization not authorized")

    with pytest.raises(RequestFailedError, match="not authorized"):
        ObjectStoreClient(api).exists("model.v2.pkl", "abc")
