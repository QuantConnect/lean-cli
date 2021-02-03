import json

import pytest
import responses
from lean.api.api_client import APIClient, BASE_URL
from lean.api.errors import FailedRequestException, AuthenticationException


@responses.activate
def test_get_should_make_get_request_to_given_endpoint() -> None:
    responses.add(responses.GET, BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient("123", "456")
    api.get("endpoint")

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == BASE_URL + "/endpoint"


@responses.activate
def test_get_should_attach_parameters_to_url() -> None:
    responses.add(responses.GET, BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient("123", "456")
    api.get("endpoint", {"key1": "value1", "key2": "value2"})

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == BASE_URL + "/endpoint?key1=value1&key2=value2"


@responses.activate
def test_post_should_make_post_request_to_given_endpoint() -> None:
    responses.add(responses.POST, BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient("123", "456")
    api.post("endpoint")

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == BASE_URL + "/endpoint"


@responses.activate
def test_post_should_set_body_of_request_as_json() -> None:
    responses.add(responses.POST, BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient("123", "456")
    api.post("endpoint", {"key1": "value1", "key2": "value2"})

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == BASE_URL + "/endpoint"

    body = json.loads(responses.calls[0].request.body)

    assert "key1" in body
    assert "key2" in body

    assert body["key1"] == "value1"
    assert body["key2"] == "value2"


@responses.activate
@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_should_make_authenticated_requests(method: str) -> None:
    responses.add(method.upper(), BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient("123", "456")
    response = getattr(api, method)("endpoint")

    assert len(responses.calls) == 1

    headers = responses.calls[0].request.headers
    assert "Timestamp" in headers
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Basic ")


@responses.activate
@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_should_return_data_if_success_is_true(method: str) -> None:
    responses.add(method.upper(), BASE_URL + "/endpoint", '{ "success": true }')

    api = APIClient("123", "456")
    response = getattr(api, method)("endpoint")

    assert "success" in response
    assert response["success"]


@responses.activate
@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_should_raise_authentication_error_on_http_500(method: str) -> None:
    responses.add(method.upper(), BASE_URL + "/endpoint", status=500)

    api = APIClient("123", "456")

    with pytest.raises(AuthenticationException):
        response = getattr(api, method)("endpoint")


@responses.activate
@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_should_raise_authentication_error_on_error_complaining_about_hash(method: str) -> None:
    responses.add(method.upper(), BASE_URL + "/endpoint", '{ "success": false, "errors": ["Hash doesn\'t match."] }')

    api = APIClient("123", "456")

    with pytest.raises(AuthenticationException):
        response = getattr(api, method)("endpoint")


@responses.activate
@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_should_raise_failed_request_error_if_response_contains_errors(method: str) -> None:
    responses.add(method.upper(), BASE_URL + "/endpoint", '{ "success": false, "errors": ["Error 1", "Error 2"] }')

    api = APIClient("123", "456")

    with pytest.raises(FailedRequestException) as ex:
        response = getattr(api, method)("endpoint")

        assert ex.message == "Error 1\nError 2"


@responses.activate
@pytest.mark.parametrize("method", [("get"), ("post")])
def test_api_client_should_raise_failed_request_error_if_response_contains_messages(method: str) -> None:
    responses.add(method.upper(),
                  BASE_URL + "/endpoint",
                  '{ "success": false, "messages": ["Message 1", "Message 2"] }')

    api = APIClient("123", "456")

    with pytest.raises(FailedRequestException) as ex:
        response = getattr(api, method)("endpoint")

        assert ex.message == "Message 1\nMessage 2"
