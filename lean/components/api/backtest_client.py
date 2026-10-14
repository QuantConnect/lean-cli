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

from typing import Any, Dict, List, Optional

from lean.components.api.api_client import *
from lean.models.api import QCBacktest


class BacktestClient:
    """The BacktestClient class contains methods to interact with backtests/* API endpoints."""

    # How often and how long to wait for the API to prepare a backtest's chart, orders or log
    _LOADING_ATTEMPTS = 30
    _LOADING_DELAY_SECONDS = 1

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new BacktestClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get(self, project_id: int, backtest_id: str) -> QCBacktest:
        """Returns the details of a backtest.

        :param project_id: the id of the project the backtest belongs to
        :param backtest_id: the id of the backtest to retrieve the details of
        :return: the details of the specified backtest
        """
        data = self._api.get("backtests/read", {
            "projectId": project_id,
            "backtestId": backtest_id
        })

        return QCBacktest(**data["backtest"])

    def create(self, project_id: int, compile_id: str, name: str, parameters: Dict[str, str] = None) -> QCBacktest:
        """Creates a new backtest.

        :param project_id: the id of the project to create a backtest for
        :param compile_id: the id of a compilation of the given project
        :param name: the name of the new backtest
        :param parameters: optional key-value parameters for the backtest
        :return: the created backtest
        """
        from lean import __version__
        payload = {
            "projectId": project_id,
            "compileId": compile_id,
            "backtestName": name,
            "requestSource": f"CLI {__version__}"
        }

        if parameters:
            payload["parameters"] = parameters

        data = self._api.post("backtests/create", payload)

        return QCBacktest(**data["backtest"])

    def delete(self, project_id: int, backtest_id: str) -> None:
        """Deletes an existing backtest.

        :param project_id: the id of the project the backtest belongs to
        :param backtest_id: the id of the backtest to delete
        """
        self._api.post("backtests/delete", {
            "projectId": project_id,
            "backtestId": backtest_id
        })

    def list(self, project_id: int) -> List[Dict[str, Any]]:
        """Returns the backtests of a project without their statistics.

        :param project_id: the id of the project
        :return: the backtests, each holding at least its backtestId, name and created time
        """
        data = self._api.post("backtests/list", {"projectId": project_id, "includeStatistics": False})
        return data.get("backtests") or []

    def read_chart(self, project_id: int, backtest_id: str, name: str, start: int, end: int,
                   count: int) -> Optional[Dict[str, Any]]:
        """Returns a chart of a backtest, sampled down to the given number of points.

        :param project_id: the id of the project the backtest belongs to
        :param backtest_id: the id of the backtest
        :param name: the name of the chart
        :param start: the start of the range to read, as a unix timestamp
        :param end: the end of the range to read, as a unix timestamp
        :param count: the number of points to sample the chart down to
        :return: the chart, or None if it is not available yet
        """
        data = self._post_when_ready("backtests/chart/read", project_id, backtest_id,
                                     {"name": name, "count": count, "start": start, "end": end})
        return data.get("chart") or None

    def read_orders(self, project_id: int, backtest_id: str, start: int, end: int) -> Dict[str, Any]:
        """Returns a page of the orders of a backtest, the API serves at most 100 orders per request.

        :param project_id: the id of the project the backtest belongs to
        :param backtest_id: the id of the backtest
        :param start: the index of the first order to read
        :param end: the index after the last order to read
        :return: the page, "orders" holding the orders and "length" the total number of orders
        """
        return self._post_when_ready("backtests/orders/read", project_id, backtest_id, {"start": start, "end": end})

    def read_log(self, project_id: int, backtest_id: str, start: int, end: int) -> Dict[str, Any]:
        """Returns a page of the log of a backtest, the API serves at most 200 lines per request.

        :param project_id: the id of the project the backtest belongs to
        :param backtest_id: the id of the backtest
        :param start: the index of the first line to read
        :param end: the index after the last line to read
        :return: the page, "logs" holding the lines and "length" the total number of lines
        """
        return self._post_when_ready("backtests/read/log", project_id, backtest_id,
                                     {"start": start, "end": end, "query": " "})

    def _post_when_ready(self, endpoint: str, project_id: int, backtest_id: str,
                         payload: Optional[Dict[str, Any]] = None) -> Any:
        """Makes a request about a backtest, retrying while the API is still preparing the data.

        The chart, orders and log endpoints prepare their data the first time it is asked for and answer
        {"status": "loading", "progress": ...} until it is ready.
        """
        from time import sleep

        data = {"projectId": project_id, "backtestId": backtest_id, **(payload or {})}
        for attempt in range(self._LOADING_ATTEMPTS):
            response = self._api.post(endpoint, data)
            if response.get("status") != "loading":
                return response
            if attempt < self._LOADING_ATTEMPTS - 1:
                sleep(self._LOADING_DELAY_SECONDS)
        raise RuntimeError(f"QuantConnect is still preparing the data of {endpoint}, try again later")
