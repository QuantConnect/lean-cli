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

from datetime import datetime
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.container import container
from lean.models.api import QCResolution, QCSecurityType
from tests.test_helpers import create_fake_lean_cli_directory


def test_data_download_forex_downloads_daily_data() -> None:
    create_fake_lean_cli_directory()

    data_downloader = mock.Mock()
    container.data_downloader.override(providers.Object(data_downloader))

    result = CliRunner().invoke(lean, ["data", "download", "forex",
                                       "--ticker", "EURUSD",
                                       "--market", "FXCM",
                                       "--resolution", "daily"])

    assert result.exit_code == 0

    data_downloader.download_data.assert_called_once_with(security_type=QCSecurityType.Forex,
                                                          ticker="eurusd",
                                                          market="fxcm",
                                                          resolution=QCResolution.Daily,
                                                          start=None,
                                                          end=None,
                                                          path_template="forex/fxcm/daily/eurusd.zip",
                                                          overwrite=False)


def test_data_download_forex_downloads_minute_data() -> None:
    create_fake_lean_cli_directory()

    data_downloader = mock.Mock()
    container.data_downloader.override(providers.Object(data_downloader))

    result = CliRunner().invoke(lean, ["data", "download", "forex",
                                       "--ticker", "EURUSD",
                                       "--market", "FXCM",
                                       "--resolution", "minute",
                                       "--start", "20200101",
                                       "--end", "20200201"])

    assert result.exit_code == 0

    data_downloader.download_data.assert_called_once_with(security_type=QCSecurityType.Forex,
                                                          ticker="eurusd",
                                                          market="fxcm",
                                                          resolution=QCResolution.Minute,
                                                          start=datetime(year=2020, month=1, day=1),
                                                          end=datetime(year=2020, month=2, day=1),
                                                          path_template="forex/fxcm/minute/eurusd/$DAY$_quote.zip",
                                                          overwrite=False)


def test_data_download_forex_passes_overwrite_flag() -> None:
    create_fake_lean_cli_directory()

    data_downloader = mock.Mock()
    container.data_downloader.override(providers.Object(data_downloader))

    result = CliRunner().invoke(lean, ["data", "download", "forex",
                                       "--ticker", "EURUSD",
                                       "--market", "FXCM",
                                       "--resolution", "daily",
                                       "--overwrite"])

    assert result.exit_code == 0

    data_downloader.download_data.assert_called_once_with(security_type=QCSecurityType.Forex,
                                                          ticker="eurusd",
                                                          market="fxcm",
                                                          resolution=QCResolution.Daily,
                                                          start=None,
                                                          end=None,
                                                          path_template="forex/fxcm/daily/eurusd.zip",
                                                          overwrite=True)


@pytest.mark.parametrize("resolution,start_end_expected", [("daily", False),
                                                           ("hour", False),
                                                           ("minute", True),
                                                           ("second", True),
                                                           ("tick", True)])
def test_data_download_forex_aborts_when_start_end_not_set_when_they_should_be(resolution: str,
                                                                               start_end_expected: bool) -> None:
    create_fake_lean_cli_directory()

    data_downloader = mock.Mock()
    container.data_downloader.override(providers.Object(data_downloader))

    result = CliRunner().invoke(lean, ["data", "download", "forex",
                                       "--ticker", "EURUSD",
                                       "--market", "FXCM",
                                       "--resolution", resolution])

    if start_end_expected:
        assert result.exit_code != 0
        data_downloader.download_data.assert_not_called()
    else:
        assert result.exit_code == 0
        data_downloader.download_data.assert_called_once()
