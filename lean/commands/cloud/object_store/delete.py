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

from lean.click import LeanCommand
from lean.container import container


@command(cls=LeanCommand)
@argument("key", type=str)
def delete(key: str) -> str:
    """
    Delete a value from the organization's cloud object store.

    :param key: The desired key name to delete.
    """
    organization_id = container.organization_manager.try_get_working_organization_id()
    api_client = container.api_client
    api_client.object_store.delete(key, organization_id)
