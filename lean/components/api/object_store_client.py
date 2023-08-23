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


class ObjectStoreClient:
    """The ObjectStoreClient class contains methods to interact with object/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new ObjectStoreClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get(self, key: str, organization_id: str) -> str:
        """Returns the details of key from the object store.

        :param key: key of the object to retrieve
        :param organization_id: the id of the organization who's object store to retrieve from
        :return: the details of the specified object
        """

        payload = {
            "organizationId": organization_id,
            "key": key,
        }

        data = self._api.post("object/get", payload)

        return data

    def set(self, key: str, objectData: bytes, organization_id: str) -> None:
        """Sets the given key in the Object Store.

        :param key: key of the object to set
        :param objectData: the data to set
        :param organization_id: the id of the organization who's object store to set data in
        """
        payload = {
            "organizationId": organization_id,
            "key": key
        }
        extra_options = {
            "files": {"objectData": objectData}
        }
        self._api.post("object/set", payload, False, extra_options)

    def list(self, path: str, organization_id: str) -> str:
        """List all values for the given root key in the Object Store.

        :param path: root key for which to list all objects
        :param organization_id: the id of the organization who's object store to retrieve from
        :return: all objects for the given root key
        """
        payload = {
            "organizationId": organization_id,
            "path": path
        }

        data = self._api.post("object/list", payload)

        return data
    
    def delete(self, key: str, organization_id: str) -> None:
        """Deletes the given key from the Object Store.

        :param key: key of the object to delete
        :param organization_id: the id of the organization who's object store to delete from
        """
        payload = {
            "organizationId": organization_id,
            "key": key
        }

        self._api.post("object/delete", payload)