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
from pathlib import Path
from typing import List, Optional

import requests
from dateutil.rrule import DAILY, rrule, rruleset, weekday

from lean.components.api.api_client import APIClient
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.util.logger import Logger
from lean.components.util.market_hours_database import MarketHoursDatabase
from lean.models.api import QCResolution, QCSecurityType
from lean.models.data import DataFile
from lean.models.errors import MoreInfoError, RequestFailedError


class DataDownloader:
    """The DataDownloader is responsible for downloading data from the QuantConnect Data Library."""

    def __init__(self,
                 logger: Logger,
                 api_client: APIClient,
                 lean_config_manager: LeanConfigManager,
                 market_hours_database: MarketHoursDatabase):
        """Creates a new CloudBacktestRunner instance.

        :param logger: the logger to use to log messages with
        :param api_client: the APIClient instance to use when communicating with the QuantConnect API
        :param lean_config_manager: the LeanConfigManager instance to retrieve the data directory from
        :param market_hours_database: the MarketHoursDatabase instance to retrieve tradable days from
        """
        self._logger = logger
        self._api_client = api_client
        self._lean_config_manager = lean_config_manager
        self._market_hours_database = market_hours_database

    def download_data(self,
                      security_type: QCSecurityType,
                      ticker: str,
                      market: str,
                      resolution: QCResolution,
                      start: Optional[datetime],
                      end: Optional[datetime],
                      path_template: str,
                      overwrite: bool) -> None:
        """Downloads files from the QuantConnect Data Library to the local data directory.

        The user should have already added the requested files to its QuantConnect account.

        :param security_type: the security type of the data
        :param ticker: the ticker of the data
        :param market: the market of the data
        :param resolution: the resolution of the data
        :param start: the start date of the data, may be None if the resolution is stored in a single file
        :param end: the end date of the data, may be None if the resolution is stored in a single file
        :param path_template: the local path of each file, $DAY$ is replaced with the current yyyyMMdd date
        :param overwrite: True if existing files should be overwritten, False if not
        """
        if start is None or end is None:
            dates = [None]
        else:
            dates = self._get_dates_with_data(security_type, market, ticker, start, end)

        files = []
        for date in dates:
            if date is None:
                path = path_template
            else:
                path = path_template.replace("$DAY$", date.strftime("%Y%m%d"))

            files.append(DataFile(
                path=path,
                security_type=security_type,
                ticker=ticker,
                market=market,
                resolution=resolution,
                date=date
            ))

        self._download_files(files, overwrite)

    def _download_files(self, files: List[DataFile], overwrite: bool) -> None:
        """Downloads files from the QuantConnect Data Library to the local data directory.

        The user should have already added the requested files to its QuantConnect account.

        :param files: the list of files to download
        :param overwrite: True if existing files should be overwritten, False if not
        """
        data_dir = self._lean_config_manager.get_data_directory()

        for index, file in enumerate(files):
            self._logger.info(f"[{index + 1}/{len(files)}] Downloading {file.path}")
            self._download_file(file, overwrite, data_dir)

    def _download_file(self, file: DataFile, overwrite: bool, data_directory: Path) -> None:
        """Downloads a single file from the QuantConnect Data Library to the local data directory.

        :param file: the file to download
        :param overwrite: True if existing files should be overwritten, False if not
        :param data_directory: the path to the local data directory
        """
        local_path = data_directory / file.path

        if local_path.exists() and not overwrite:
            self._logger.warn(f"{local_path} already exists, use --overwrite to overwrite it")
            return

        try:
            link = self._api_client.data.get_link(file.security_type,
                                                  file.ticker,
                                                  file.market,
                                                  file.resolution,
                                                  file.date)
            link = link.link
        except RequestFailedError as error:
            if "Data not found for the given information" in str(error):
                raise MoreInfoError(
                    f"Please add {file.get_url()} to your QuantConnect account and run this command again",
                    "https://www.quantconnect.com/docs/v2/lean-cli/tutorials/local-data/downloading-from-quantconnect#02-QuantConnect-Data-Library")
            raise error

        local_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(link)
        response.raise_for_status()

        if response.headers["content-type"] == "application/json":
            response_data = response.json()
            if "message" in response_data and "Not found" in response_data["message"]:
                self._logger.warn(f"{file.path} does not exist in the QuantConnect Data Library")
                return

        with local_path.open("wb+") as f:
            f.write(response.content)

    def _get_dates_with_data(self,
                             security_type: QCSecurityType,
                             market: str,
                             symbol: str,
                             start: datetime,
                             end: datetime) -> List[datetime]:
        """Returns the dates between two dates for which the QuantConnect Data Library has data.

        The QuantConnect Data Library has data for all tradable days.
        This method uses the market hours database to find the tradable weekdays and the holidays.

        :param security_type: the security type of the data
        :param market: the market of the data
        :param symbol: the symbol of the data
        :param start: the inclusive start date
        :param end: the inclusive end date
        """
        entry = self._market_hours_database.get_entry(security_type, market, symbol)

        # Create the set of rules containing all date rules
        rules = rruleset()

        # There is data on all weekdays on which the security trades
        weekdays_with_data = []
        for index, day in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            if len(getattr(entry, day)) > 0:
                weekdays_with_data.append(weekday(index))
        rules.rrule(rrule(DAILY, dtstart=start, until=end, byweekday=weekdays_with_data))

        # There is no data for holidays
        for holiday in entry.holidays:
            rules.exdate(holiday)

        # Return the dates of all tradable weekdays minus the holidays
        return rules.between(start, end, inc=True)
