import json
from pathlib import Path
from typing import Dict

from lean.config.global_config import GlobalConfig
from lean.constants import GLOBAL_CONFIG_DIR

CONFIG_FILE_NAME = "credentials"


def get_config_path() -> Path:
    return Path.home() / GLOBAL_CONFIG_DIR / CONFIG_FILE_NAME


def create_config(user_id: str, api_token: str) -> None:
    with open(get_config_path(), "w+") as file:
        json.dump({"user_id": user_id, "api_token": api_token}, file)


def get_config() -> Dict[str, str]:
    with open(get_config_path()) as file:
        return json.load(file)


def test_constructor_loads_existing_data() -> None:
    create_config("123", "456")

    config = GlobalConfig(CONFIG_FILE_NAME)

    assert "user_id" in config
    assert "api_token" in config

    assert config["user_id"] == "123"
    assert config["api_token"] == "456"


def test_save_saves_modifications_to_existing_file() -> None:
    create_config("123", "456")

    config = GlobalConfig(CONFIG_FILE_NAME)
    config["user_id"] = "789"
    config.save()

    new_config = get_config()

    assert "user_id" in new_config
    assert "api_token" in new_config

    assert new_config["user_id"] == "789"
    assert new_config["api_token"] == "456"


def test_save_creates_file_if_it_does_not_exist_yet() -> None:
    config = GlobalConfig(CONFIG_FILE_NAME)
    config["user_id"] = "123"
    config["api_token"] = "456"
    config.save()

    new_config = get_config()

    assert "user_id" in new_config
    assert "api_token" in new_config

    assert new_config["user_id"] == "123"
    assert new_config["api_token"] == "456"


def test_clear_empties_the_dict() -> None:
    config = GlobalConfig(CONFIG_FILE_NAME)
    config["user_id"] = "123"
    config["api_token"] = "456"

    config.clear()

    assert len(config.keys()) == 0


def test_clear_deletes_the_underlying_file() -> None:
    create_config("123", "456")

    config = GlobalConfig(CONFIG_FILE_NAME)
    config.clear()

    assert not get_config_path().exists()
