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
from pathlib import Path

import pytest
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
