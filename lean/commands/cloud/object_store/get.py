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

from uuid import uuid4
from os import path, getcwd, unlink, mkdir

from click import command, option, argument
from lean.click import LeanCommand
from lean.container import container


@command(cls=LeanCommand)
@argument("key", type=str, nargs=-1)
@option("--destination-folder", type=str, default="",
          help=f"The destination folder to download the object store values,"
               f" if not provided will use to current directory")
def get(key: [str], destination_folder: str):
    """
    Download an object store value to disk from the organization's cloud object store.

    :param key: The desired key to fetch, multiple can be provided.
    """
    organization_id = container.organization_manager.try_get_working_organization_id()
    api_client = container.api_client
    logger = container.logger

    logger.info(f"Fetching object store download url")
    url = api_client.object_store.get(key, organization_id, logger)
    if not destination_folder:
        destination_folder = getcwd()

    if not path.exists(destination_folder):
        mkdir(destination_folder)

    temp_file = path.join(destination_folder, f"{str(uuid4())}.zip")

    with logger.transient_progress() as progress:
        progress.add_task(f"Start downloading keys into {temp_file}:", total=None)
        logger.debug(f"Downloading: {url}")

        api_client.data.download_url(url, temp_file, lambda advance: None)

    logger.info(f"Unzipping object store keys values into: '{destination_folder}'")
    from zipfile import ZipFile
    with ZipFile(temp_file, 'r') as zip_ref:
        zip_ref.extractall(destination_folder)

    if path.exists(temp_file):
        logger.debug(f"Deleting temp file: '{temp_file}'")
        unlink(temp_file)
