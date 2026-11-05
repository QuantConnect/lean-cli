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

from lean.components.util.object_store_helper import get_key_issues, key_to_save, sanitize_key

RULES = "Keys may only contain english letters, numbers, spaces and the characters '.', '/', '_', '#', '-', '$' and '=', " \
        "never two '.' in a row, e.g. 'folder/trade_log-2024.v2.csv'"


@pytest.mark.parametrize("key", ["my_key", "./my_key/nested/file.csv", "file with spaces #1-$=.txt", "folder/trade_log-2024.csv",
                                 "folder.v1/file.tar.gz", ".hidden/file.name_v2", "trailing.", "a/"])
def test_get_key_issues_returns_none_for_a_supported_key(key: str) -> None:
    assert get_key_issues(key) is None


@pytest.mark.parametrize("key,expected_issue", [
    ("trade log: AI & Cloud.csv", "unsupported characters ':', '&'"),
    ("résumé.pdf", "unsupported character 'é'"),
    ("folder\\file.csv", "unsupported character '\\'"),
    ("..model.pkl", "it contains '..'"),
    ("a/../b.csv", "it contains '..'"),
    ("trade log: AI..v2.csv", "unsupported character ':'; it contains '..'"),
    (".", "it has no name, only '.' and separators"),
    ("./", "it has no name, only '.' and separators"),
    ("/", "it has no name, only '.' and separators"),
    ("", "the key is empty"),
    ("a" + "/" * 101, "it has more than 100 '/' separators"),
])
def test_get_key_issues_states_the_issue_and_the_rules(key: str, expected_issue: str) -> None:
    assert get_key_issues(key) == f"{expected_issue}. {RULES}"


@pytest.mark.parametrize("key,expected", [
    ("trade_log_ai_hardware_&_cloud.csv", "trade_log_ai_hardware___cloud.csv"),
    ("trade log: AI & Cloud.csv", "trade log_ AI _ Cloud.csv"),
    ("résumé.pdf", "r_sum_.pdf"),
    ("a..", "a__"),
    ("a...b.csv", "a___b.csv"),
    ("100%.json", "100_.json"),
    ("../prefix/file", "__/prefix/file"),
    ("a/../b.csv", "a/__/b.csv"),
    ("..model.pkl", "__model.pkl"),
    ("folder\\file.csv", "folder/file.csv"),
    ("file.csv\n", "file.csv_"),
])
def test_sanitize_key_returns_a_supported_key(key: str, expected: str) -> None:
    sanitized = sanitize_key(key)

    assert sanitized == expected
    assert get_key_issues(sanitized) is None


@pytest.mark.parametrize("key,expected", [
    ("../secrets.json", "__/secrets.json"),
    ("../../secrets.json", "__/__/secrets.json"),
    ("..\\secrets.json", "__/secrets.json"),
    ("./../secrets.json", "./__/secrets.json"),
    ("x/../secrets.json", "x/__/secrets.json"),
    ("x/../../secrets.json", "x/__/__/secrets.json"),
    ("x\\..\\..\\secrets.json", "x/__/__/secrets.json"),
    ("x/.../secrets.json", "x/___/secrets.json"),
    ("x/..", "x/__"),
    ("x/....", "x/____"),
])
def test_traversal_keys_are_sanitized_so_they_cannot_leave_the_storage_root(key: str, expected: str) -> None:
    assert "it contains '..'" in get_key_issues(key)
    assert sanitize_key(key) == expected
    assert ".." not in sanitize_key(key)


@pytest.mark.parametrize("key", ["", ".", "./", "/", "a" + "/" * 101])
def test_sanitize_key_raises_when_the_key_cannot_be_fixed(key: str) -> None:
    with pytest.raises(RuntimeError, match="is not supported"):
        sanitize_key(key)


def test_sanitize_key_is_lossy_and_distinct_keys_can_collide() -> None:
    assert sanitize_key("trade_log_ai&cloud.csv") == sanitize_key("trade_log_ai:cloud.csv") == "trade_log_ai_cloud.csv"


def test_key_to_save_keeps_a_supported_key_without_checking_the_store() -> None:
    logger = mock.Mock()
    exists = mock.Mock()

    assert key_to_save("folder/trade_log-2024.csv", exists, logger) == "folder/trade_log-2024.csv"

    exists.assert_not_called()
    logger.warn.assert_not_called()


def test_key_to_save_sanitizes_an_unsupported_key_with_a_warning() -> None:
    logger = mock.Mock()

    assert key_to_save("trade log: AI & Cloud.csv", lambda key: False, logger) == "trade log_ AI _ Cloud.csv"

    logger.warn.assert_called_once_with(
        f"Key 'trade log: AI & Cloud.csv' is not supported: unsupported characters ':', '&'. {RULES}. "
        "Using 'trade log_ AI _ Cloud.csv' instead")


def test_key_to_save_raises_when_the_sanitized_key_already_holds_an_object() -> None:
    logger = mock.Mock()

    with pytest.raises(RuntimeError) as error:
        key_to_save("report (1).csv", lambda key: key == "report _1_.csv", logger)

    assert str(error.value) == "Key 'report (1).csv' is not supported and its sanitized name 'report _1_.csv' already holds " \
                               "another object. Delete 'report _1_.csv' or set it directly to replace it"
