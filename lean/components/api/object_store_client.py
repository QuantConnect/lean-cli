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
from lean.components.util.logger import Logger


class ObjectStoreClient:
    """The ObjectStoreClient class contains methods to interact with object/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new ObjectStoreClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def properties(self, key: str, organization_id: str) -> str:
        """Returns the details of key from the object store.
        :param key: key of the object to retrieve
        :param organization_id: the id of the organization who's object store to retrieve from
        :return: the details of the specified object
        """
        payload = {
            "organizationId": organization_id,
            "key": key,
        }

        return self._api.post("object/properties", payload)

    def get(self, keys: [str], organization_id: str, logger: Logger) -> str:
        """Will fetch an url to download the requested keys
        :param keys: keys of the object to retrieve
        :param organization_id: the id of the organization who's object store to retrieve from
        :param logger: the logger instance to use
        :return: the url to download the requested keys
        """

        payload = {
            "organizationId": organization_id,
            "keys": keys,
        }

        data = self._api.post("object/get", payload)
        if "url" in data and data["url"]:
            # we got the url right away
            return data["url"]

        job_id = data["jobId"]
        if job_id:
            from time import sleep
            payload = {
                "organizationId": organization_id,
                "jobId": job_id,
            }

            with logger.transient_progress() as progress:
                progress.add_task("Waiting for files to be ready for download:", total=None)

                # we will retry up to 5 min to get the url
                retry_count = 0
                while not data["url"]:
                    sleep(3)
                    data = self._api.post("object/get", payload)
                    retry_count = retry_count + 1
                    if retry_count > ((60 * 5) / 3):
                        raise TimeoutError(f"Timeout waiting for object store job id {job_id}, please contact support")
        else:
            raise ValueError("JobId was not found in API response")

        return data["url"]

    def set(self, key: str, object_data: bytes, organization_id: str) -> None:
        """Sets the given key in the Object Store.
        :param key: key of the object to set
        :param object_data: the data to set
        :param organization_id: the id of the organization who's object store to set data in
        """
        payload = {
            "organizationId": organization_id,
            "key": key
        }
        extra_options = {
            "files": {"objectData": object_data}
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
