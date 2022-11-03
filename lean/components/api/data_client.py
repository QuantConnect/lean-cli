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

from lean.components.api.api_client import *
from lean.models.api import QCDataInformation
from typing import List, Callable


class DataClient:
    """The DataClient class contains methods to interact with data/* API endpoints."""

    _list_files_cache: Dict[str, List[str]] = {}

    def __init__(self, api_client: 'APIClient', http_client: 'HTTPClient') -> None:
        """Creates a new DataClient instance.

        :param api_client: the APIClient instance to use when making requests
        :param http_client: the HTTPClient instance to use when downloading files
        """
        self._api = api_client
        self._http_client = http_client

    def download_file(self, relative_file_path: str, organization_id: str,
                      local_filename: str, progress_callback: Callable[[float], None]) -> None:
        """Downloads the content of a downloadable data file.

        :param relative_file_path: the relative path of the data file
        :param organization_id: the id of the organization that should be billed
        :param local_filename: the final local path where the data file will be stored
        :param progress_callback: the download progress callback
        """
        from tempfile import NamedTemporaryFile
        from shutil import move
        from os import path, makedirs

        data = self._api.post("data/read", {
            "format": "link",
            "filePath": relative_file_path,
            "organizationId": organization_id
        })

        # we stream the data into a temporary file and later move it to it's final location
        with self._http_client.get(data["link"], stream=True) as r:
            r.raise_for_status()
            total_size = 0
            try:
                total_size = int(r.headers['Content-length'])
            except:
                pass
            current_size = 0
            with NamedTemporaryFile(delete=False) as f:
                temp_file_name = f.name
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if total_size != 0:
                        previous = current_size / total_size

                    current_size += f.write(chunk)

                    if total_size != 0:
                        # progressive progress update if we can
                        progress_callback((current_size / total_size) - previous)
            if total_size == 0:
                # if total size not available update progress at the end
                progress_callback(1)

            directory = path.dirname(local_filename)
            makedirs(directory, exist_ok=True)
            move(temp_file_name, local_filename)

    def download_public_file(self, data_endpoint: str) -> bytes:
        """Downloads the content of a downloadable public file.

        :param data_endpoint: the url of the public file
        :return: the content of the file
        """
        return self._http_client.get(data_endpoint).content

    def list_files(self, prefix: str) -> List[str]:
        """Lists all remote files with a given prefix.

        :param prefix: the prefix of the files to return
        :return: the list of files with the given prefix
        """
        if prefix in DataClient._list_files_cache:
            return DataClient._list_files_cache[prefix]

        data = self._api.post("data/list", {
            "filePath": prefix
        })

        first_part = prefix.split("/")[0]
        files = sorted(f"{first_part}/{obj}" for obj in data["objects"])

        DataClient._list_files_cache[prefix] = files

        return files

    def get_info(self, organization_id: str) -> QCDataInformation:
        """Returns the available data vendors, their prices and a link to the data agreement.

        :param organization_id: the id of the organization to retrieve the data information for
        :return: the latest information on the downloadable data
        """
        data = self._api.post("data/prices", {
            "organizationId": organization_id
        })

        return QCDataInformation(**data)
