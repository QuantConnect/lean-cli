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
from lean.components.api.auth0_client import Auth0Client
from lean.components.util.http_client import HTTPClient


@responses.activate
def test_auth0client_trade_station() -> None:
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
    assert len(result.authorization) > 0
    assert len(result.get_authorization_config_without_account()) > 0
    assert len(result.get_account_ids()) > 0


def test_auth0client_authorize_with_user_name() -> None:
    with mock.patch("webbrowser.open") as mock_open:
        Auth0Client.authorize("charles-schwab", mock.Mock(), 123, user_name="test_login")
        mock_open.assert_called_once()
        called_url = mock_open.call_args[0][0]
        assert "&userId=test_login" in called_url


def test_auth0client_authorize_without_user_name() -> None:
    with mock.patch("webbrowser.open") as mock_open:
        Auth0Client.authorize("charles-schwab", mock.Mock(), 123)
        mock_open.assert_called_once()
        called_url = mock_open.call_args[0][0]
        assert "userId" not in called_url


@responses.activate
def test_auth0client_read_with_user_name() -> None:
    api_clint = APIClient(mock.Mock(), HTTPClient(mock.Mock()), user_id="123", api_token="abc")

    responses.add(
        responses.POST,
        f"{API_BASE_URL}live/auth0/read",
        json={
            "authorization": {
                "charles-schwab-access-token": "abc123",
                "accounts": [{"id": "ACC001", "name": "ACC001 | Individual | USD"}]
            },
            "success": "true"},
        status=200
    )

    result = api_clint.auth0.read("charles-schwab", user_name="test_login")

    assert result
    assert result.authorization
    sent_body = responses.calls[0].request.body.decode()
    assert "userId" in sent_body
    assert "test_login" in sent_body


@responses.activate
def test_auth0client_read_without_user_name() -> None:
    api_clint = APIClient(mock.Mock(), HTTPClient(mock.Mock()), user_id="123", api_token="abc")

    responses.add(
        responses.POST,
        f"{API_BASE_URL}live/auth0/read",
        json={
            "authorization": {
                "charles-schwab-access-token": "abc123",
                "accounts": [{"id": "ACC001", "name": "ACC001 | Individual | USD"}]
            },
            "success": "true"},
        status=200
    )

    result = api_clint.auth0.read("charles-schwab")

    assert result
    assert result.authorization
    sent_body = responses.calls[0].request.body.decode()
    assert "userId" not in sent_body


@responses.activate
def test_auth0client_alpaca() -> None:
    api_clint = APIClient(mock.Mock(), HTTPClient(mock.Mock()), user_id="123", api_token="abc")

    responses.add(
        responses.POST,
        f"{API_BASE_URL}live/auth0/read",
        json={
            "authorization": {
                "alpaca-access-token": "XXXX-XXX-XXX-XXX-XXXXX-XX",
                "accounts": [{"id": "XXXX-XXX-XXX-XXX-XXXXX-XX", "name": " |USD"}]
            },
            "success": "true"},
        status=200
    )

    brokerage_id = "TestBrokerage"

    result = api_clint.auth0.read(brokerage_id)

    assert result
    assert result.authorization
    assert len(result.authorization) > 0
    assert len(result.get_authorization_config_without_account()) > 0
    assert len(result.get_account_ids()) > 0
