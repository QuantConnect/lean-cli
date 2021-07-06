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
import requests
from responses import RequestsMock

from lean.components.util.http_client import HTTPClient

EXAMPLE_URL = "https://example.com/"


@pytest.mark.parametrize("method,use_request", [("get", False),
                                                ("get", True),
                                                ("post", False),
                                                ("post", True)])
def test_http_client_makes_request(requests_mock: RequestsMock, method: str, use_request: bool) -> None:
    requests_mock.add(method.upper(), EXAMPLE_URL, "Example body")

    http_client = HTTPClient(mock.Mock())

    if use_request:
        response = http_client.request(method, EXAMPLE_URL)
    else:
        response = getattr(http_client, method)(EXAMPLE_URL)

    assert response.text == "Example body"


@pytest.mark.parametrize("method,use_request", [("get", False),
                                                ("get", True),
                                                ("post", False),
                                                ("post", True)])
def test_http_client_raises_when_request_unsuccessful(requests_mock: RequestsMock,
                                                      method: str,
                                                      use_request: bool) -> None:
    requests_mock.add(method.upper(), EXAMPLE_URL, status=404)

    http_client = HTTPClient(mock.Mock())

    with pytest.raises(requests.HTTPError):
        if use_request:
            http_client.request(method, EXAMPLE_URL)
        else:
            getattr(http_client, method)(EXAMPLE_URL)


@pytest.mark.parametrize("method,use_request", [("get", False),
                                                ("get", True),
                                                ("post", False),
                                                ("post", True)])
def test_http_client_does_not_raise_when_raise_for_status_false(requests_mock: RequestsMock,
                                                                method: str,
                                                                use_request: bool) -> None:
    requests_mock.add(method.upper(), EXAMPLE_URL, status=404)

    http_client = HTTPClient(mock.Mock())

    if use_request:
        response = http_client.request(method, EXAMPLE_URL, raise_for_status=False)
    else:
        response = getattr(http_client, method)(EXAMPLE_URL, raise_for_status=False)

    assert response.status_code == 404


@pytest.mark.parametrize("method,use_request", [("get", False),
                                                ("get", True),
                                                ("post", False),
                                                ("post", True)])
def test_http_client_logs_debug_message_about_request(requests_mock: RequestsMock,
                                                      method: str,
                                                      use_request: bool) -> None:
    requests_mock.add(method.upper(), EXAMPLE_URL, "Example body")

    logger = mock.Mock()
    http_client = HTTPClient(logger)

    if use_request:
        http_client.request(method, EXAMPLE_URL)
    else:
        getattr(http_client, method)(EXAMPLE_URL)

    logger.debug.assert_called_once()


@pytest.mark.parametrize("method,use_request", [("get", False),
                                                ("get", True),
                                                ("post", False),
                                                ("post", True)])
def test_http_client_logs_debug_message_about_response_when_unsuccessful(requests_mock: RequestsMock,
                                                                         method: str,
                                                                         use_request: bool) -> None:
    requests_mock.add(method.upper(), EXAMPLE_URL, "Example body", status=404)

    logger = mock.Mock()
    http_client = HTTPClient(logger)

    with pytest.raises(requests.HTTPError):
        if use_request:
            http_client.request(method, EXAMPLE_URL)
        else:
            getattr(http_client, method)(EXAMPLE_URL)

    assert logger.debug.call_count == 2
