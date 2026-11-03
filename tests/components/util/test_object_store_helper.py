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

RULES = "Keys may only contain english letters, numbers, spaces and the characters '/', '\\', '_', '#', '-', '$' and '=', " \
        "plus at most one '.' followed by a letters-and-numbers-only extension, e.g. 'folder/trade_log-2024.csv'"


@pytest.mark.parametrize("key", ["my_key", "./my_key/nested\\file.csv", "file with spaces #1-$=.txt", "folder/trade_log-2024.csv", "/"])
def test_get_key_issues_returns_none_for_a_supported_key(key: str) -> None:
    assert get_key_issues(key) is None


@pytest.mark.parametrize("key,expected_issue", [
    ("trade log: AI & Cloud.csv", "unsupported characters ':', '&'"),
    ("résumé.pdf", "unsupported character 'é'"),
    ("file.tar.gz", "it has 2 '.' but at most one '.extension' is allowed"),
    ("file.name_v2", "the extension 'name_v2' may only contain letters and numbers"),
    ("folder.v1/file", "the extension 'v1/file' may only contain letters and numbers"),
    ("trade log: AI.v2.csv", "unsupported character ':'; it has 2 '.' but at most one '.extension' is allowed"),
    (".", "it has no name before the '.'"),
    ("..model.pkl", "it starts with more than one '.'"),
    ("", "the key is empty"),
    ("a" + "/" * 101, "it has more than 100 '/' or '\\' separators"),
])
def test_get_key_issues_states_the_issue_and_the_rules(key: str, expected_issue: str) -> None:
    assert get_key_issues(key) == f"{expected_issue}. {RULES}"


@pytest.mark.parametrize("key,expected", [
    ("trade_log_ai_hardware_&_cloud.csv", "trade_log_ai_hardware___cloud.csv"),
    ("trade log: AI & Cloud.csv", "trade log_ AI _ Cloud.csv"),
    ("file.tar.gz", "file_tar.gz"),
    ("résumé.pdf", "r_sum_.pdf"),
    ("a..", "a__"),
    ("100%.json", "100_.json"),
    ("../prefix/file", "__/prefix/file"),
    (".", "_"),
    ("..model.pkl", "__model.pkl"),
])
def test_sanitize_key_returns_a_supported_key(key: str, expected: str) -> None:
    sanitized = sanitize_key(key)

    assert sanitized == expected
    assert get_key_issues(sanitized) is None


@pytest.mark.parametrize("key", ["", "a" + "/" * 101])
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
