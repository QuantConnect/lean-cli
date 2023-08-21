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
@argument("root-key", type=str)
def list(root_key: str) -> str:
    """
    List all values for the given root key in the organization's object store.
    
    """
    organization_id = container.organization_manager.try_get_working_organization_id()
    api_client = container.api_client
    logger = container.logger
    data = api_client.object_store.list(root_key, organization_id)

    try:
        total_objects = len(data['objects'])
        logger.info(f"Found {total_objects} objects for key {root_key}")
        for object in data['objects']:
            logger.info('\n')
            for k, v in object.items():
                logger.info(f"{k}: {v}")
    except KeyError as e:
        logger.error(f"Key {root_key} not found.")
    except Exception as e:
        logger.error(f"Error: {e}")