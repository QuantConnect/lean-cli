from pathlib import Path
from typing import Optional
from unittest import mock

import click

from lean.config.lean_config import get_lean_config, get_lean_config_path
from lean.constants import DEFAULT_LEAN_CONFIG_FILE


def set_config_option(get_current_context, config_option: Optional[str]) -> None:
    ctx = click.Context(click.Command(""))
    ctx.config_option = config_option
    get_current_context.return_value = ctx


@mock.patch("click.get_current_context")
def test_get_lean_config_path_should_return_file_from_context_if_set(get_current_context) -> None:
    set_config_option(get_current_context, str(Path.cwd() / "custom-config.json"))

    result = get_lean_config_path()

    assert result == Path.cwd() / "custom-config.json"


@mock.patch("click.get_current_context")
def test_get_lean_config_path_should_look_into_parent_directories_for_config_file(get_current_context) -> None:
    set_config_option(get_current_context, None)
    (Path.home() / DEFAULT_LEAN_CONFIG_FILE).touch()

    result = get_lean_config_path()

    assert result == Path.home() / DEFAULT_LEAN_CONFIG_FILE


@mock.patch("click.get_current_context")
def test_get_lean_config_path_should_return_none_if_no_config_file_available(get_current_context) -> None:
    set_config_option(get_current_context, None)

    result = get_lean_config_path()

    assert result is None


@mock.patch("lean.config.lean_config.get_lean_config_path")
def test_get_lean_config_should_read_and_parse_config_file_containing_comments(get_lean_config_path) -> None:
    config_path = Path.cwd() / DEFAULT_LEAN_CONFIG_FILE

    with open(config_path, "w+") as file:
        file.write("""
{
    // Key 1
    "key1": "value1", // Additional documentation for key 1
    
    // Key 2
    "key2": "value2",
    
    // Key 3
    "key3": "value3"
}
        """)

    get_lean_config_path.return_value = config_path

    result = get_lean_config()

    assert "key1" in result
    assert "key2" in result
    assert "key3" in result

    assert result["key1"] == "value1"
    assert result["key2"] == "value2"
    assert result["key3"] == "value3"


@mock.patch("lean.config.lean_config.get_lean_config_path")
def test_get_lean_config_should_return_none_if_no_config_file_available(get_lean_config_path) -> None:
    get_lean_config_path.return_value = None

    result = get_lean_config()

    assert result is None
