from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from lean.components.cloud.data_downloader import DataDownloader, _store_local_file

VALID_DATABASE = '{"entries": {}}'


@pytest.fixture
def tmp_path() -> Path:
    # The test suite runs on a fake filesystem (see conftest.py), so use a fixed path instead of pytest's tmp_path
    path = Path("/data")
    path.mkdir(parents=True)
    return path


def _create_downloader(data_dir: Path, market_hours: bytes) -> DataDownloader:
    lean_config_manager = mock.Mock()
    lean_config_manager.get_lean_config.return_value = {}
    lean_config_manager.get_data_directory.return_value = data_dir
    api_client = mock.Mock()
    api_client.data.download_public_file.side_effect = \
        lambda url: market_hours if url.endswith(".json") else b"symbol,properties\n"
    return DataDownloader(mock.Mock(), api_client, lean_config_manager, "0.00:00:01")


def _market_hours_file(data_dir: Path) -> Path:
    path = data_dir / "market-hours" / "market-hours-database.json"
    path.parent.mkdir(parents=True)
    path.write_text(VALID_DATABASE, encoding="utf-8")
    return path


def test_update_database_files_keeps_existing_file_when_response_is_malformed(tmp_path: Path) -> None:
    path = _market_hours_file(tmp_path)

    _create_downloader(tmp_path, b"not json").update_database_files()

    assert path.read_text(encoding="utf-8") == VALID_DATABASE


def test_update_database_files_keeps_existing_file_when_entries_are_missing(tmp_path: Path) -> None:
    path = _market_hours_file(tmp_path)

    _create_downloader(tmp_path, b'{"other": 1}').update_database_files()

    assert path.read_text(encoding="utf-8") == VALID_DATABASE


def test_update_database_files_replaces_file_with_valid_commented_response(tmp_path: Path) -> None:
    path = _market_hours_file(tmp_path)
    new_content = b'/* comment */ {"entries": {"Equity-usa-[*]": {}}}'

    _create_downloader(tmp_path, new_content).update_database_files()

    assert path.read_bytes() == new_content


def test_store_local_file_leaves_no_temporary_files(tmp_path: Path) -> None:
    path = tmp_path / "dir" / "file.json"

    _store_local_file(b"content", path)

    assert path.read_bytes() == b"content"
    assert [p.name for p in path.parent.iterdir()] == ["file.json"]
