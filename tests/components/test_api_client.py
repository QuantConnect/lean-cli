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

import json
import re
from unittest import mock

import pytest
from responses import RequestsMock

from lean.components.api_client import APIClient
from lean.models.errors import AuthenticationError, RequestFailedError

BASE_URL = "https://www.quantconnect.com/api"


def test_get_makes_get_request_to_given_endpoint(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET, BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")
    api.get("endpoint")

    assert len(requests_mock.calls) == 1
    assert requests_mock.calls[0].request.url == BASE_URL + "/endpoint"


def test_get_attaches_parameters_to_url(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.GET, BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")
    api.get("endpoint", {"key1": "value1", "key2": "value2"})

    assert len(requests_mock.calls) == 1
    assert requests_mock.calls[0].request.url == BASE_URL + "/endpoint?key1=value1&key2=value2"


def test_post_makes_post_request_to_given_endpoint(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.POST, BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")
    api.post("endpoint")

    assert len(requests_mock.calls) == 1
    assert requests_mock.calls[0].request.url == BASE_URL + "/endpoint"


def test_post_sets_body_of_request_as_json(requests_mock: RequestsMock) -> None:
    requests_mock.add(requests_mock.POST, BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")
    api.post("endpoint", {"key1": "value1", "key2": "value2"})

    assert len(requests_mock.calls) == 1
    assert requests_mock.calls[0].request.url == BASE_URL + "/endpoint"

    body = json.loads(requests_mock.calls[0].request.body)

    assert body["key1"] == "value1"
    assert body["key2"] == "value2"


@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_makes_authenticated_requests(method: str, requests_mock: RequestsMock) -> None:
    requests_mock.add(method.upper(), BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")
    getattr(api, method)("endpoint")

    assert len(requests_mock.calls) == 1

    headers = requests_mock.calls[0].request.headers
    assert "Timestamp" in headers
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Basic ")


@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_returns_data_when_success_is_true(method: str, requests_mock: RequestsMock) -> None:
    requests_mock.add(method.upper(), BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")
    response = getattr(api, method)("endpoint")

    assert "success" in response
    assert response["success"]


@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_raises_authentication_error_on_http_500(method: str, requests_mock: RequestsMock) -> None:
    requests_mock.add(method.upper(), BASE_URL + "/endpoint", status=500)

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")

    with pytest.raises(AuthenticationError):
        getattr(api, method)("endpoint")


@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_raises_request_failed_error_on_failing_response_non_http_500(method: str,
                                                                                 requests_mock: RequestsMock) -> None:
    requests_mock.add(method.upper(), BASE_URL + "/endpoint", status=404)

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")

    with pytest.raises(RequestFailedError):
        getattr(api, method)("endpoint")


@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_raises_authentication_error_on_error_complaining_about_hash(method: str,
                                                                                requests_mock: RequestsMock) -> None:
    requests_mock.add(method.upper(), BASE_URL + "/endpoint",
                      '{ "success": false, "errors": ["Hash doesn\'t match."] }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")

    with pytest.raises(AuthenticationError):
        getattr(api, method)("endpoint")


@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_raises_request_failed_error_when_response_contains_errors(method: str,
                                                                              requests_mock: RequestsMock) -> None:
    requests_mock.add(method.upper(), BASE_URL + "/endpoint", '{ "success": false, "errors": ["Error 1", "Error 2"] }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")

    with pytest.raises(RequestFailedError) as error:
        getattr(api, method)("endpoint")

    assert str(error.value) == "Error 1\nError 2"


@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_raises_request_failed_error_when_response_contains_messages(method: str,
                                                                                requests_mock: RequestsMock) -> None:
    requests_mock.add(method.upper(),
                      BASE_URL + "/endpoint",
                      '{ "success": false, "messages": ["Message 1", "Message 2"] }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")

    with pytest.raises(RequestFailedError) as error:
        getattr(api, method)("endpoint")

    assert str(error.value) == "Message 1\nMessage 2"


def test_is_authenticated_returns_true_when_authenticated_request_succeeds(requests_mock: RequestsMock) -> None:
    requests_mock.assert_all_requests_are_fired = False
    requests_mock.add(requests_mock.GET, re.compile(".*"), body='{ "success": true }')
    requests_mock.add(requests_mock.POST, re.compile(".*"), body='{ "success": true }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")

    assert api.is_authenticated()


def test_is_authenticated_returns_false_when_authenticated_request_fails(requests_mock: RequestsMock) -> None:
    requests_mock.assert_all_requests_are_fired = False
    requests_mock.add(requests_mock.GET, re.compile(".*"), body='{ "success": false }')
    requests_mock.add(requests_mock.POST, re.compile(".*"), body='{ "success": false }')

    api = APIClient(mock.Mock(), BASE_URL, "123", "456")

    assert not api.is_authenticated()
