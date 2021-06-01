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
from lean.models.api import QCNode, QCNodeList


class NodeClient:
    """The NodeClient class contains methods to interact with nodes/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new NodeClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get_all(self, organization_id: str) -> QCNodeList:
        """Returns all the nodes in an organization.

        :param organization_id: the id of the organization to retrieve the nodes for
        :return: the nodes in the specified organization
        """
        data = self._api.post("nodes/read", {
            "organizationId": organization_id
        })

        return QCNodeList(**data)

    def create(self, organization_id: str, name: str, sku: str) -> QCNode:
        """Creates a new node.

        :param organization_id: the id of the organization to create the node in
        :param name: the name of the node to create
        :param sku: the sku of the node to create
        :return: the created node
        """
        data = self._api.post("nodes/create", {
            "organizationId": organization_id,
            "name": name,
            "sku": sku
        })

        return QCNode(**data["node"])

    def update(self, organization_id: str, node_id: str, new_name: str) -> None:
        """Updates an existing node.

        :param organization_id: the id of the organization the node belongs to
        :param node_id: the id of the node to update
        :param new_name: the new name to assign to the node
        :return: the updated node
        """
        self._api.post("nodes/update", {
            "organizationId": organization_id,
            "nodeId": node_id,
            "name": new_name
        })

    def delete(self, organization_id: str, node_id: str) -> None:
        """Deletes an existing node.

        :param organization_id: the id of the organization the node belongs to
        :param node_id: the id of the node to delete
        """
        self._api.post("nodes/delete", {
            "organizationId": organization_id,
            "nodeId": node_id
        })

    def stop(self, organization_id: str, node_id: str) -> None:
        """Stops the current activity on a node.

        :param organization_id: the id of the organization the node belongs to
        :param node_id: the id of the node to stop the current activity for
        """
        self._api.post("nodes/stop", {
            "organizationId": organization_id,
            "nodeId": node_id
        })
