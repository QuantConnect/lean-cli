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

from click import argument
from lean.commands.cloud.object_store import object_store
from lean.click import LeanCommand
from lean.container import container


@object_store.command(cls=LeanCommand, name="list", aliases=["ls"])
@argument("key", type=str, default="/")
def list(key: str) -> str:
    """
    List all values for the given root key in the organization's cloud object store.
    """
    organization_id = container.organization_manager.try_get_working_organization_id()
    api_client = container.api_client
    logger = container.logger
    data = api_client.object_store.list(key, organization_id)

    try:
        headers = ["key", "size", "folder", "name"]
        display_headers = ["Key", "Bytes", "Folder", "Filename"]
        rows = [[str(obj.get(header, "")) for header in headers] for obj in data['objects']]
        # sort rows by key
        rows.sort(key=lambda x: x[0])
        all_rows = [display_headers] + rows
        column_widths = [max(len(row[i]) for row in all_rows) for i in range(len(all_rows[0]))]
        for row in all_rows:
            logger.info("  ".join(value.ljust(width) for value, width in zip(row, column_widths)))
    except KeyError as e:
        logger.error(f"Key {key} not found.")
    except Exception as e:
        logger.error(f"Error: {e}")