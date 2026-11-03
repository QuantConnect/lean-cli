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

import re
from typing import Callable, List, Optional

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.util.logger import Logger

# The key rules of LEAN's ObjectStore (QuantConnect/Lean#9905), mirrored by set only so a key set here is the one an
# algorithm saves to. The other commands send the key as typed; LEAN's reads also fall back to the sanitized key
_SUPPORTED_KEY = re.compile(r"\.?[a-zA-Z0-9\\/_#\-$= ]+\.?[a-zA-Z0-9]*")
_UNSUPPORTED_CHARACTERS = re.compile(r"[^a-zA-Z0-9\\/_#\-$= .]")
_EXTENSION = re.compile(r"[a-zA-Z0-9]+")
_KEY_RULES = "Keys may only contain english letters, numbers, spaces and the characters '/', '\\', '_', '#', '-', '$' and '=', " \
             "plus at most one '.' followed by a letters-and-numbers-only extension, e.g. 'folder/trade_log-2024.csv'"


def key_to_save(key: str, exists: Callable[[str], bool], logger: Logger) -> str:
    """Returns the key a set goes to: the given one when it follows the key format, else its sanitized version,
    warning about the rewrite. Raises when the sanitized key already holds an object, as LEAN's save does: nothing
    records who wrote it, so it is only replaced through its exact key.

    :param key: the key as given by the user
    :param exists: whether an object is stored under a key
    :param logger: the logger to warn with
    :return: the key to send to the object store
    """
    issues = get_key_issues(key)
    if issues is None:
        return key

    sanitized = sanitize_key(key)
    logger.warn(f"Key '{key}' is not supported: {issues}. Using '{sanitized}' instead")
    if exists(sanitized):
        raise RuntimeError(f"Key '{key}' is not supported and its sanitized name '{sanitized}' already holds another object. "
                           f"Delete '{sanitized}' or set it directly to replace it")
    return sanitized


def get_key_issues(key: str) -> Optional[str]:
    """Describes why a key does not follow the key format: the problems found and the rules.

    :param key: the key to check
    :return: the issues with the key, or None when it is supported
    """
    if _is_supported_key(key):
        return None
    return "; ".join(_find_key_issues(key)) + ". " + _KEY_RULES


def sanitize_key(key: str) -> str:
    """Converts an unsupported key into a supported one by replacing every unsupported character with '_',
    keeping at most the final '.extension': 'trade log: AI & Cloud.csv' becomes 'trade log_ AI _ Cloud.csv'.

    :param key: the key to sanitize
    :return: a key following the key format
    """
    sanitized = _UNSUPPORTED_CHARACTERS.sub("_", key)

    # a single trailing '.extension' of letters and numbers is allowed: keep the last dot if it
    # introduces a valid extension and replace every other dot
    last_dot = sanitized.rfind(".")
    if last_dot > 0 and _EXTENSION.fullmatch(sanitized[last_dot + 1:]) is not None:
        sanitized = sanitized[:last_dot].replace(".", "_") + sanitized[last_dot:]
    elif last_dot >= 0:
        sanitized = sanitized.replace(".", "_")

    issues = get_key_issues(sanitized)
    if issues is not None:
        raise RuntimeError(f"Key '{key}' is not supported: {issues}")
    return sanitized


def _is_supported_key(key: str) -> bool:
    return bool(key) and _SUPPORTED_KEY.fullmatch(key) is not None and key.count("/") <= 100 and key.count("\\") <= 100


def _find_key_issues(key: str) -> List[str]:
    """Lists why a key is not supported, one entry per problem found."""
    if not key:
        return ["the key is empty"]

    issues = []
    unsupported = list(dict.fromkeys(f"'{char}'" for char in _UNSUPPORTED_CHARACTERS.findall(key)))
    if unsupported:
        issues.append(f"unsupported character{'s' if len(unsupported) > 1 else ''} {', '.join(unsupported)}")

    # a single leading '.' is allowed, every other '.' must introduce the final extension
    name = key.lstrip(".")
    dots = name.count(".")
    if dots > 1:
        issues.append(f"it has {dots} '.' but at most one '.extension' is allowed")
    elif dots == 1:
        extension = name[name.index(".") + 1:]
        if extension and _EXTENSION.fullmatch(extension) is None:
            issues.append(f"the extension '{extension}' may only contain letters and numbers")
    if not name:
        issues.append("it has no name before the '.'")
    elif key.startswith(".."):
        issues.append("it starts with more than one '.'")

    if key.count("/") > 100 or key.count("\\") > 100:
        issues.append("it has more than 100 '/' or '\\' separators")

    if not issues:
        issues.append("it does not follow the key format")
    return issues



def open_storage_directory_in_explorer(lean_config_manager: LeanConfigManager):
    """Opens the storage directory in the file explorer."""
    global_storage_directory_path = lean_config_manager.get_cli_root_directory() / "storage"
    if not global_storage_directory_path.exists():
        global_storage_directory_path.mkdir(parents=True)
    open_file_explorer(str(global_storage_directory_path))
    
def open_file_explorer(directory_path: str):
    """Opens the given directory in the file explorer."""
    from webbrowser import open
    open('file:///' + directory_path)