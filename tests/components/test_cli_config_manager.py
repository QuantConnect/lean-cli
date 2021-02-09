from unittest import mock

import pytest

from lean.components.cli_config_manager import CLIConfigManager


def test_cli_config_manager_get_option_by_key_should_return_option_with_matching_key() -> None:
    manager = CLIConfigManager(mock.Mock(), mock.Mock())

    for key in ["user-id", "api-token", "default-language"]:
        assert manager.get_option_by_key(key).key == key


def test_cli_config_manager_get_option_by_key_should_raise_error_when_no_option_with_matching_key_exists() -> None:
    manager = CLIConfigManager(mock.Mock(), mock.Mock())

    with pytest.raises(Exception):
        manager.get_option_by_key("this-option-does-not-exist")
