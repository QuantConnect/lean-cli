import re
from pathlib import Path
from typing import Any, Dict, Optional

import click
from jsoncomment import JsonComment

from lean.constants import DEFAULT_LEAN_CONFIG_FILE


def get_lean_config_path() -> Optional[Path]:
    """Find the nearest lean.json by recursively going upwards in the directory tree."""
    # --config overrides the default search for lean.json
    ctx = click.get_current_context()
    if ctx.config_option is not None:
        return Path(ctx.config_option)

    # Recurse upwards in the directory tree until we find a lean.json file
    current_dir = Path.cwd()
    while True:
        target_file = current_dir / DEFAULT_LEAN_CONFIG_FILE
        if target_file.exists():
            return target_file

        if current_dir.parent == current_dir:
            return None

        current_dir = current_dir.parent


def get_lean_config() -> Optional[Dict[str, Any]]:
    """Read and parse the configuration stored in the nearest lean.json."""
    lean_config_path = get_lean_config_path()

    if lean_config_path is None:
        return None

    with open(lean_config_path) as file:
        config = file.read()
        config_without_inline_comments = re.sub(r",\s*//.*", ",", config, flags=re.MULTILINE)
        return JsonComment().loads(config_without_inline_comments)
