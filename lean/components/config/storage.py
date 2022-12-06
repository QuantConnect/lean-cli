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
from typing import Any


def safe_save(data: str, path: str, _retry: int = 0):
    from uuid import uuid4
    from shutil import move
    from os import unlink, path as os_path
    from time import time, sleep

    lock_file = Path(str(path) + '.lock').resolve()
    try:
        with open(lock_file, 'x') as _:
            # we create a tmp file we will use to write to. This was we avoid concurrency issues corrupting the file
            tmp_file = Path(str(path) + '.' + str(uuid4())).resolve()
            with open(tmp_file, "w+", encoding="utf-8") as targetFile:
                targetFile.write(data)

            # atomic move when on the same filesystem which is this case, they are side by side
            move(tmp_file, path)
        unlink(lock_file)
    except FileExistsError:
        try:
            # lock is taken, delete if old, else wait and retry
            if time() - os_path.getmtime(lock_file) >= 2:
                unlink(lock_file)
            else:
                sleep(0.250)
        except:
            # some else might have deleted it
            pass
        if _retry < 10:
            safe_save(data, path, ++_retry)


class Storage:
    """A Storage instance manages the data in a single JSON file."""

    def __init__(self, file: str) -> None:
        """Creates a new Storage instance.

        :param file: the path to the file this Storage instance should manage
        """
        from json import loads

        self.file = Path(file)

        if self.file.exists():
            try:
                content = self.file.read_text(encoding="utf-8")
                if content:
                    self._data = loads(content)
                else:
                    self._data = {}
            except:
                # Could happen rarely due to concurrency or unexpected failures, so if it does let's recover
                self.file.unlink()
                self._data = {}
        else:
            self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Returns the value assigned to the given key.

        Returns a default value when nothing is assigned to the given key.

        :param key: the key to retrieve the value of
        :param default: the default value to return when key is not set
        :return: the value assigned to the key or default if the key is not set
        """
        if key in self._data:
            return self._data[key]
        else:
            return default

    def set(self, key: str, value: Any) -> None:
        """Assigns a value to a key.

        The value is stored as json, so must be serializable using json.dump().

        :param key: the key to assign the value to
        :param value: the json-serializable value to assign to the given key
        """
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        """Deletes a key.

        :param key: the key to delete
        """
        self._data.pop(key, None)
        self._save()

    def has(self, key: str) -> bool:
        """Returns whether the Storage instance has a value assigned to the given key.

        :param key: the key to check the existence of
        :return: True if a value is assigned to the given key, False if not
        """
        return key in self._data

    def clear(self) -> None:
        """Clears the Storage instance and deletes the underlying file."""
        self._data.clear()
        self._save()

    def _save(self) -> None:
        from json import dumps

        """Saves the data to the underlying file, deleting the file if there is no data."""
        if len(self._data) > 0:
            self.file.parent.mkdir(parents=True, exist_ok=True)

            safe_save(data=dumps(self._data, indent=4) + "\n", path=self.file.resolve())
        else:
            if self.file.exists():
                self.file.unlink()
