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

from pathlib import Path
from typing import Dict, Any, Optional
from json import loads, JSONDecodeError


def parse_json_safely(json_string: str) -> Dict[str, Any]:
    """
    Attempts to parse a JSON string with multiple fallback strategies.
    
    This function is designed to handle JSON strings that may have been
    mangled by Windows shells (PowerShell/CMD) which strip or escape quotes.
    
    :param json_string: The JSON string to parse
    :return: Parsed dictionary
    :raises ValueError: If all parsing attempts fail
    """
    if not json_string or json_string.strip() == "":
        return {}
    
    # Try standard JSON parsing first
    try:
        return loads(json_string)
    except JSONDecodeError as e:
        original_error = str(e)
    
    # Try fixing common Windows shell issues
    # Try single quotes to double quotes (common Windows PowerShell issue)
    try:
        return loads(json_string.replace("'", '"'))
    except JSONDecodeError:
        pass
    
    # If all attempts fail, provide helpful error message
    raise ValueError(
        f"Failed to parse JSON configuration. Original error: {original_error}\n"
        f"Input: {json_string}\n\n"
        f"On Windows, JSON strings may be mangled by the shell. Consider using --extra-docker-config-file instead.\n"
        f"Example: Create a file 'docker-config.json' with your configuration and use:\n"
        f"  --extra-docker-config-file docker-config.json"
    )


def load_json_from_file_or_string(
    json_string: Optional[str] = None,
    json_file: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Loads JSON configuration from either a string or a file.
    
    If both json_file and json_string are provided, json_file takes precedence.
    
    :param json_string: JSON string to parse (optional)
    :param json_file: Path to JSON file (optional)
    :return: Parsed dictionary, or empty dict if both parameters are None
    :raises ValueError: If parsing fails or if file doesn't exist
    """
    # Validate that both parameters aren't provided (though we allow it, file takes precedence)
    if json_file is not None and json_string is not None:
        # Log a warning would be ideal, but we'll prioritize file as documented
        pass
    
    if json_file is not None:
        if not json_file.exists():
            raise ValueError(f"Configuration file not found: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read()
                return loads(content)
        except JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON from file {json_file}: {e}\n"
                f"Please ensure the file contains valid JSON."
            )
        except Exception as e:
            raise ValueError(f"Failed to read file {json_file}: {e}")
    
    if json_string is not None:
        return parse_json_safely(json_string)
    
    return {}
