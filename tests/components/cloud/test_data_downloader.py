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
from unittest import mock

import pytest

from lean.components.cloud.data_downloader import DataDownloader

LOCAL_DATABASE = '{"entries": {"Equity-usa-[*]": {}}}'


def _update_database_files(downloaded_database: bytes) -> Path:
    data_dir = Path.cwd() / "data"
    database_path = data_dir / "market-hours" / "market-hours-database.json"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.write_text(LOCAL_DATABASE, encoding="utf-8")

    lean_config_manager = mock.Mock()
    lean_config_manager.get_lean_config.return_value = {}
    lean_config_manager.get_data_directory.return_value = data_dir
    api_client = mock.Mock()
    api_client.data.download_public_file.side_effect = [b"symbol,property\n", downloaded_database]

    DataDownloader(mock.Mock(), api_client, lean_config_manager, "1.00:00:00").update_database_files()
    return database_path


@pytest.mark.parametrize("downloaded_database", [b"not json", b"", b"null", b"[]", b'{"other": {}}',
                                                 b'{"entries": []}', b"\xff"])
def test_update_database_files_keeps_market_hours_database_when_download_is_invalid(downloaded_database: bytes) -> None:
    database_path = _update_database_files(downloaded_database)

    assert database_path.read_text(encoding="utf-8") == LOCAL_DATABASE


def test_update_database_files_replaces_market_hours_database_with_valid_download() -> None:
    downloaded_database = b'/*\n comment\n*/\n{"entries": {"Forex-oanda-[*]": {}}}'

    database_path = _update_database_files(downloaded_database)

    assert database_path.read_bytes() == downloaded_database
