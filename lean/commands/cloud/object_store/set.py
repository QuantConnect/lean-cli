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

from click import command, argument
from pathlib import Path
from lean.click import LeanCommand, PathParameter
from lean.container import container


@command(cls=LeanCommand)
@argument("key", type=str)
@argument("path", type= PathParameter(exists=True, file_okay=True, dir_okay=False))
def set(key: str, path: Path) -> None:
    """Sets the data to the given key in the organization's cloud object store.

    :param key: The key to set the data to.
    :param path: Path to the file containing the object data.
    """
    organization_id = container.organization_manager.try_get_working_organization_id()
    container.logger.info(f"Setting object {key} in organization {organization_id}")
    api_client = container.api_client
    with open(path, "rb") as file:
        bytes_data: bytes = file.read()
    api_client.object_store.set(key, bytes_data, organization_id)
