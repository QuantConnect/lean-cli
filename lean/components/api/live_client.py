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

from datetime import datetime
from typing import List, Optional

from lean.components.api.api_client import *
from lean.models.api import QCFullLiveAlgorithm, QCLiveAlgorithmStatus, QCMinimalLiveAlgorithm, QCNotificationMethod, QCRestResponse


class LiveClient:
    """The LiveClient class contains methods to interact with live/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new LiveClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get_project_by_id(self,
                          project_id: str) -> QCFullLiveAlgorithm:
        """Retrieves all live algorithms.

        :param project_id: the project id
        :return: a live algorithm which match the given filters
        """
        parameters = {"projectId": project_id}
        response = self._api.get("live/read", parameters)

        if response:
            response["projectId"] = project_id
            return QCFullLiveAlgorithm(**response)

        return None

    def start(self,
              project_id: int,
              compile_id: str,
              node_id: str,
              brokerage_settings: Dict[str, Any],
              live_data_providers_settings: Dict[str, Any],
              automatic_redeploy: bool,
              version_id: int,
              notify_order_events: bool,
              notify_insights: bool,
              notify_methods: List[QCNotificationMethod],
              live_cash_balance: Optional[List[Dict[str, float]]] = None,
              live_holdings: Optional[List[Dict[str, float]]] = None) -> QCMinimalLiveAlgorithm:
        """Starts live trading for a project.

        :param project_id: the id of the project to start live trading for
        :param compile_id: the id of the compile to use for live trading
        :param node_id: the id of the node to start live trading on
        :param brokerage_settings: the brokerage settings to use
        :param live_data_providers_settings: the live data providers settings to use
        :param automatic_redeploy: whether automatic redeploys are enabled
        :param version_id: the id of the LEAN version to use
        :param notify_order_events: whether notifications should be sent on order events
        :param notify_insights: whether notifications should be sent on insights
        :param notify_methods: the places to send notifications to
        :param live_cash_balance: the list of initial cash balance
        :param live_holdings: the list of initial portfolio holdings
        :return: the created live algorithm
        """

        if live_cash_balance:
            brokerage_settings["cash"] = live_cash_balance
        if live_holdings:
            brokerage_settings["holdings"] = live_holdings

        parameters = {
            "projectId": project_id,
            "compileId": compile_id,
            "nodeId": node_id,
            "brokerage": brokerage_settings,
            "dataProviders": live_data_providers_settings,
            "automaticRedeploy": automatic_redeploy,
            "versionId": version_id
        }

        if notify_order_events or notify_insights:
            events = []
            if notify_order_events:
                events.append("orderEvent")
            if notify_insights:
                events.append("insight")

            parameters["notification"] = {
                "events": events,
                "targets": [{x: y for x, y in method.dict().items() if y} for method in notify_methods]
            }

        data = self._api.post("live/create", parameters)
        return QCMinimalLiveAlgorithm(**data)

    def stop(self, project_id: int) -> QCRestResponse:
        """Stops live trading for a certain project without liquidated existing positions.

        :param project_id: the id of the project to stop live trading for
        """
        data = self._api.post("live/update/stop", {
            "projectId": project_id
        })
        return QCRestResponse(**data)

    def liquidate_and_stop(self, project_id: int) -> QCRestResponse:
        """Stops live trading and liquidates existing positions for a certain project.

        :param project_id: the id of the project to stop live trading and liquidate existing positions for
        """
        data = self._api.post("live/update/liquidate", {
            "projectId": project_id
        })
        return QCRestResponse(**data)

    def command_create(self, project_id: int, command: dict) -> QCRestResponse:
        """Sends a command to a live trading deployment

        :param project_id: the id of the project
        :param command: the command to send
        """
        data = self._api.post("live/commands/create", {
            "projectId": project_id,
            "command": command
        })
        return QCRestResponse(**data)
