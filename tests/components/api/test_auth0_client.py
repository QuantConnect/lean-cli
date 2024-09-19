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
import responses
from lean.constants import API_BASE_URL
from components.api.test_clients import create_api_client


@responses.activate
def test_auth0client() -> None:
    os.environ.setdefault("QC_API", "local")
    api_clint = create_api_client()

    responses.add(
        responses.POST,
        f"{API_BASE_URL}live/auth0/read",
        json={
            "authorization": {
                "test-brokerage-client-id": "123",
                "test-brokerage-refresh-token": "123"
            },
            "accountIds": ["123", "321"],
            "success": "true"
        },
        status=200
    )

    brokerage_id = "TestBrokerage"

    result = api_clint.auth0.read(brokerage_id)

    assert result
    assert result.authorization
    assert len(result.authorization) > 0
    assert result.accountIds
    assert len(result.accountIds) > 0
