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

import json
import os
import stat
import sys
from pathlib import Path

import pytest
from pyfakefs.helpers import get_gid, get_uid, reset_ids, set_gid, set_uid
from requests.exceptions import JSONDecodeError
from responses import RequestsMock

import lean.models as models


def _write_cache(path: Path) -> str:
    content = json.dumps({"modules": {"SavedModule": {"version": "1.0"}}})
    path.write_text(content, encoding="utf-8")
    return content


def test_download_modules_json_keeps_cache_when_response_is_not_json(requests_mock: RequestsMock,
                                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    cache = Path.cwd() / "cache" / "modules.json"
    cache.parent.mkdir()
    content = _write_cache(cache)
    monkeypatch.setattr(models, "file_path", cache)
    requests_mock.add(requests_mock.GET, models.url, body="not json", status=200)

    with pytest.raises(JSONDecodeError):
        models._download_modules_json()

    assert cache.read_text(encoding="utf-8") == content
    assert [p.name for p in cache.parent.iterdir()] == ["modules.json"]


def test_download_modules_json_replaces_cache_with_valid_response(requests_mock: RequestsMock,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    cache = Path.cwd() / "cache" / "modules.json"
    cache.parent.mkdir()
    _write_cache(cache)
    monkeypatch.setattr(models, "file_path", cache)
    new_modules = {"modules": {"NewModule": {"version": "2.0"}}}
    requests_mock.add(requests_mock.GET, models.url, json=new_modules, status=200)

    models._download_modules_json()

    assert json.loads(cache.read_text(encoding="utf-8")) == new_modules
    assert [p.name for p in cache.parent.iterdir()] == ["modules.json"]


@pytest.mark.skipif(sys.platform == "win32", reason="File ownership and modes are POSIX only")
def test_download_modules_json_keeps_cache_owner_and_mode_when_refreshed_as_root(requests_mock: RequestsMock,
                                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    cache = Path.cwd() / "cache" / "modules.json"
    cache.parent.mkdir()
    _write_cache(cache)
    os.chown(cache, 1000, 1000)
    os.chmod(cache, 0o644)
    monkeypatch.setattr(models, "file_path", cache)
    new_modules = {"modules": {"NewModule": {"version": "2.0"}}}
    requests_mock.add(requests_mock.GET, models.url, json=new_modules, status=200)

    set_uid(0)
    set_gid(0)
    previous_umask = os.umask(0o077)
    try:
        models._download_modules_json()
    finally:
        os.umask(previous_umask)
        set_uid(1000)
        set_gid(1000)

    try:
        cache_stat = os.stat(cache)
        assert (cache_stat.st_uid, cache_stat.st_gid, stat.S_IMODE(cache_stat.st_mode)) == (1000, 1000, 0o644)
        assert json.loads(cache.read_text(encoding="utf-8")) == new_modules
    finally:
        reset_ids()


@pytest.mark.skipif(sys.platform == "win32", reason="File ownership and modes are POSIX only")
def test_download_modules_json_keeps_cache_when_its_owner_cannot_be_kept(requests_mock: RequestsMock,
                                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    cache = Path.cwd() / "cache" / "modules.json"
    cache.parent.mkdir()
    content = _write_cache(cache)
    os.chown(cache, get_uid() + 1, get_gid() + 1)
    monkeypatch.setattr(models, "file_path", cache)
    requests_mock.add(requests_mock.GET, models.url, json={"modules": {}}, status=200)

    def chown(*args, **kwargs) -> None:
        raise PermissionError("Operation not permitted")

    monkeypatch.setattr(os, "chown", chown)

    with pytest.raises(PermissionError):
        models._download_modules_json()

    assert cache.read_text(encoding="utf-8") == content
    assert [p.name for p in cache.parent.iterdir()] == ["modules.json"]


@pytest.mark.skipif(sys.platform == "win32", reason="File ownership and modes are POSIX only")
@pytest.mark.parametrize("group_offset", [0, 1])
def test_download_modules_json_replaces_cache_when_only_its_group_cannot_be_kept(requests_mock: RequestsMock,
                                                                                 monkeypatch: pytest.MonkeyPatch,
                                                                                 group_offset: int) -> None:
    cache = Path.cwd() / "cache" / "modules.json"
    cache.parent.mkdir()
    _write_cache(cache)
    os.chown(cache, get_uid(), get_gid() + group_offset)
    monkeypatch.setattr(models, "file_path", cache)
    new_modules = {"modules": {"NewModule": {"version": "2.0"}}}
    requests_mock.add(requests_mock.GET, models.url, json=new_modules, status=200)

    def chown(*args, **kwargs) -> None:
        raise PermissionError("Operation not permitted")

    monkeypatch.setattr(os, "chown", chown)

    models._download_modules_json()

    assert json.loads(cache.read_text(encoding="utf-8")) == new_modules
    assert [p.name for p in cache.parent.iterdir()] == ["modules.json"]
