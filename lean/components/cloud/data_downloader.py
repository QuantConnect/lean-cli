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

import multiprocessing
from pathlib import Path
from typing import Any, List, Callable

from joblib import delayed, Parallel

from lean.components.api.api_client import APIClient
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.util.logger import Logger
from lean.models.errors import RequestFailedError


class DataDownloader:
    """The DataDownloader is responsible for downloading data from QuantConnect Datasets."""

    def __init__(self, logger: Logger, api_client: APIClient, lean_config_manager: LeanConfigManager):
        """Creates a new CloudBacktestRunner instance.

        :param logger: the logger to use to log messages with
        :param api_client: the APIClient instance to use when communicating with the QuantConnect API
        :param lean_config_manager: the LeanConfigManager instance to retrieve the data directory from
        """
        self._logger = logger
        self._api_client = api_client
        self._lean_config_manager = lean_config_manager

    def download_files(self, data_files: List[Any], overwrite: bool, organization_id: str) -> None:
        """Downloads files from QuantConnect Datasets to the local data directory.

        :param data_files: the list of data files to download
        :param overwrite: whether existing files may be overwritten
        :param organization_id: the id of the organization that should be billed
        """
        progress = self._logger.progress(suffix="{task.percentage:0.0f}% ({task.completed:,.0f}/{task.total:,.0f})")
        progress_task = progress.add_task("", total=len(data_files))

        try:
            parallel = Parallel(n_jobs=max(1, multiprocessing.cpu_count() - 1), backend="threading")

            data_dir = self._lean_config_manager.get_data_directory()
            parallel(delayed(self._download_file)(data_file.file, overwrite, data_dir, organization_id,
                                                  lambda: progress.update(progress_task, advance=1))
                     for data_file in data_files)

            progress.stop()
        except KeyboardInterrupt as e:
            progress.stop()
            raise e

    def _download_file(self,
                       relative_file: str,
                       overwrite: bool,
                       data_directory: Path,
                       organization_id: str,
                       callback: Callable[[], None]) -> None:
        """Downloads a single file from QuantConnect Datasets to the local data directory.

        If this method downloads a map or factor files zip file,
        it also updates the Lean config file to ensure LEAN uses those files instead of the csv files.

        :param relative_file: the relative path to the file in the data directory
        :param overwrite: whether existing files may be overwritten
        :param data_directory: the path to the local data directory
        :param organization_id: the id of the organization that should be billed
        :param callback: the lambda that is called just before the method returns
        """
        local_path = data_directory / relative_file

        if local_path.exists() and not overwrite:
            self._logger.warn("\n".join([
                f"{local_path} already exists, use --overwrite to overwrite it",
                "You have not been charged for this file"
            ]))
            callback()
            return

        try:
            file_content = self._api_client.data.download_file(relative_file, organization_id)
        except RequestFailedError as error:
            self._logger.warn(f"{local_path}: {error}\nYou have not been charged for this file")
            callback()
            return

        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open("wb+") as f:
            f.write(file_content)

        if relative_file.startswith("equity/usa/map_files/map_files_") and relative_file.endswith(".zip"):
            self._lean_config_manager.set_properties({
                "map-file-provider": "QuantConnect.Data.Auxiliary.LocalZipMapFileProvider"
            })

        if relative_file.startswith("equity/usa/factor_files/factor_files_") and relative_file.endswith(".zip"):
            self._lean_config_manager.set_properties({
                "factor-file-provider": "QuantConnect.Data.Auxiliary.LocalZipFactorFileProvider"
            })

        callback()
