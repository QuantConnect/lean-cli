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

import responses
from unittest import mock
from lean.constants import API_BASE_URL
from lean.components.api.api_client import APIClient
from lean.components.util.http_client import HTTPClient


@responses.activate
def test_auth0client() -> None:
    api_clint = APIClient(mock.Mock(), HTTPClient(mock.Mock()), user_id="123", api_token="abc")

    responses.add(
        responses.POST,
        f"{API_BASE_URL}live/auth0/read",
        json={
            "authorization": {
                "trade-station-client-id": "123",
                "trade-station-refresh-token": "456",
                "accounts": [
                    {"id": "11223344", "name": "11223344 | Margin | USD"},
                    {"id": "55667788", "name": "55667788 | Futures | USD"}
                ]
            },
            "success": "true"},
        status=200
    )

    brokerage_id = "TestBrokerage"

    result = api_clint.auth0.read(brokerage_id)

    assert result
    assert result.authorization
    assert len(result.authorization.client_info) > 0
    assert len(result.authorization.accounts) > 0
    assert len(result.authorization.get_account_ids()) > 0
