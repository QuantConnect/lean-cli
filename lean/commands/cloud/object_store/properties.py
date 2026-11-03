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
def properties(key: str):
    """
    Get a value properties from the organization's cloud object store.

    :param key: The desired key to fetch the properties for.
    """
    organization_id = container.organization_manager.try_get_working_organization_id()
    api_client = container.api_client
    logger = container.logger
    data = api_client.object_store.properties(key, organization_id)

    try:
        headers = ["size", "modified", "key", "preview"]
        display_headers = ["Bytes", "Modified", "Filename", "Preview"]
        data_row = []
        for header in headers:
            if header == "preview":
                value = str(data["metadata"].get(header, "N/A"))
                data_row.append(_clean_up_preview(value))
            else:
                value = str(data["metadata"].get(header, ""))
                data_row.append(value)
        all_rows = [display_headers] + [data_row]
        column_widths = [max(len(row[i]) for row in all_rows) for i in range(len(all_rows[0]))]
        for row in all_rows:
            logger.info("  ".join(value.ljust(width) for value, width in zip(row, column_widths)))
    except KeyError as e:
        logger.error(f"Key {key} not found.")
    except Exception as e:
        logger.error(f"Error: {e}")


def _clean_up_preview(preview: str) -> str:
    return preview.rstrip()[:10]
