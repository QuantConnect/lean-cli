import json
from pathlib import Path
from typing import Dict

import click
import pytest

from lean.config.global_config import ChoiceOption, GlobalConfig, StringOption
from lean.constants import GLOBAL_CONFIG_DIR

CONFIG_FILE_NAME = "credentials"


def get_config_path() -> Path:
    return Path.home() / GLOBAL_CONFIG_DIR / CONFIG_FILE_NAME


def create_config(key1: str, key2: str) -> None:
    with open(get_config_path(), "w+") as file:
        json.dump({"key1": key1, "key2": key2}, file)


def get_config() -> Dict[str, str]:
    with open(get_config_path()) as file:
        return json.load(file)


def test_global_config_constructor_should_load_existing_data() -> None:
    create_config("123", "456")

    config = GlobalConfig(CONFIG_FILE_NAME)

    assert "key1" in config
    assert "key2" in config

    assert config["key1"] == "123"
    assert config["key2"] == "456"


def test_global_config_save_should_save_modifications_to_existing_file() -> None:
    create_config("123", "456")

    config = GlobalConfig(CONFIG_FILE_NAME)
    config["key1"] = "789"
    config.save()

    new_config = get_config()

    assert "key1" in new_config
    assert "key2" in new_config

    assert new_config["key1"] == "789"
    assert new_config["key2"] == "456"


def test_global_config_save_should_create_file_when_it_does_not_exist_yet() -> None:
    config = GlobalConfig(CONFIG_FILE_NAME)
    config["key1"] = "123"
    config["key2"] = "456"
    config.save()

    new_config = get_config()

    assert "key1" in new_config
    assert "key2" in new_config

    assert new_config["key1"] == "123"
    assert new_config["key2"] == "456"


def test_global_config_clear_should_empty_dict() -> None:
    config = GlobalConfig(CONFIG_FILE_NAME)
    config["key1"] = "123"
    config["key2"] = "456"

    config.clear()

    assert len(config.keys()) == 0


def test_global_config_clear_should_delete_underlying_file() -> None:
    create_config("123", "456")

    config = GlobalConfig(CONFIG_FILE_NAME)
    config.clear()

    assert not get_config_path().exists()


def test_string_option_get_value_should_retrieve_value_from_global_config() -> None:
    create_config("123", "456")

    option = StringOption("key1", "Description 1", CONFIG_FILE_NAME)

    assert option.get_value() == "123"


def test_string_option_get_value_should_return_default_if_key_not_set_in_global_config() -> None:
    option = StringOption("key1", "Description 1", CONFIG_FILE_NAME)

    assert option.get_value(default="123") == "123"


def test_string_option_set_value_should_update_global_file() -> None:
    option = StringOption("key1", "Description 1", CONFIG_FILE_NAME)
    option.set_value("789")

    config = get_config()

    assert "key1" in config
    assert config["key1"] == "789"


def test_string_option_set_value_should_fail_when_value_blank() -> None:
    option = StringOption("key1", "Description 1", CONFIG_FILE_NAME)

    with pytest.raises(click.ClickException):
        option.set_value("")


def test_choice_option_constructor_should_add_allowed_values_to_description() -> None:
    option = ChoiceOption("key1", "Description 1", CONFIG_FILE_NAME, ["value 1", "value 2"])

    assert "value 1" in option.description
    assert "value 2" in option.description


def test_choice_option_set_value_should_update_global_file_case_insensitively() -> None:
    option = ChoiceOption("key1", "Description 1", CONFIG_FILE_NAME, ["value 1", "value 2"])
    option.set_value("VALUE 1")

    config = get_config()

    assert "key1" in config
    assert config["key1"] == "value 1"


def test_choice_option_set_value_should_fail_when_value_not_in_allowed_values() -> None:
    option = ChoiceOption("key1", "Description 1", CONFIG_FILE_NAME, ["value 1", "value 2"])

    with pytest.raises(click.ClickException):
        option.set_value("value 3")
