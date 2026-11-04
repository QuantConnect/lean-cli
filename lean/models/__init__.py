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

from os import chmod, getpid, path, remove, replace, stat
from json import load
from pathlib import Path
from stat import S_IMODE
from sys import platform
from time import time

json_modules = {}
file_name = "modules-1.15.json"
directory = Path(__file__).parent
file_path = directory.parent / file_name

# check if new file is available online
url = f"https://cdn.quantconnect.com/cli/{file_name}"


def _download_modules_json() -> None:
    """Downloads the modules JSON file from the CDN and saves it to disk."""
    from requests import get
    res = get(url, timeout=5)
    if res.ok:
        from json import dump
        # Decode the response and write a temporary file first, so a malformed response
        # or a failed write leaves the existing file untouched; the process id keeps
        # concurrent refreshes from sharing the temporary file.
        data = res.json()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_file_path = file_path.with_name(f"{file_path.name}.{getpid()}.tmp")
        try:
            with open(temporary_file_path, 'w', encoding='utf-8') as f:
                dump(data, f, ensure_ascii=False, indent=4)
            if platform != "win32" and path.exists(file_path):
                # The replacement takes the existing file's owner and mode, so a refresh run with sudo
                # doesn't leave a file that later runs without it can't read
                from os import chown
                existing = stat(file_path)
                chown(temporary_file_path, existing.st_uid, existing.st_gid)
                chmod(temporary_file_path, S_IMODE(existing.st_mode))
            replace(temporary_file_path, file_path)
        finally:
            if path.exists(temporary_file_path):
                remove(temporary_file_path)
    else:
        res.raise_for_status()


error = None
try:
    # fetch if file not available, still the empty placeholder the package ships, or fetched before 1 day
    if not path.exists(file_path) or path.getsize(file_path) == 0 or (time() - path.getmtime(file_path) > 86400):
        _download_modules_json()
except Exception as e:
    # No need to do anything if file isn't available
    error = str(e)
    pass

# check if file exists
if not Path(file_path).is_file() or path.getsize(file_path) == 0:
    error_message = f": {error}" if error is not None else ""
    raise FileNotFoundError(
        f"Modules json not found in the given path {file_path}{error_message}")

with open(file_path) as f:
    data = load(f)
    json_modules = data['modules']
