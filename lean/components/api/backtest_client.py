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

from typing import List

from lean.components.api.api_client import *
from lean.models.api import QCBacktest, QCBacktestReport


class BacktestClient:
    """The BacktestClient class contains methods to interact with backtests/* API endpoints."""

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

    def get_all(self, project_id: int) -> List[QCBacktest]:
        """Returns all backtests in a project.

        :param project_id: the id of the project to retrieve the backtests of
        :return: the backtests in the specified project
        """
        data = self._api.get("backtests/read", {
            "projectId": project_id
        })

        return [QCBacktest(**backtest) for backtest in data["backtests"]]

    def create(self, project_id: int, compile_id: str, name: str) -> QCBacktest:
        """Creates a new backtest.

        :param project_id: the id of the project to create a backtest for
        :param compile_id: the id of a compilation of the given project
        :param name: the name of the new backtest
        :return: the created backtest
        """
        data = self._api.post("backtests/create", {
            "projectId": project_id,
            "compileId": compile_id,
            "backtestName": name,
            "requestSource": f"CLI {lean.__version__}"
        })

        return QCBacktest(**data["backtest"])

    def get_report(self, project_id: int, backtest_id: str) -> QCBacktestReport:
        """Returns the report of a backtest.

        :param project_id: the id of the project the backtest belongs to
        :param backtest_id: the id of the backtest to retrieve the report of
        :return: the report of the specified backtest
        """
        data = self._api.post("backtests/read/report", {
            "projectId": project_id,
            "backtestId": backtest_id
        })

        return QCBacktestReport(**data)

    def update(self, project_id: int, backtest_id: str, name: str, note: str) -> None:
        """Updates an existing backtest.

        :param project_id: the id of the project the backtest belongs to
        :param backtest_id: the id of the backtest to update
        :param name: the new name to assign to the backtest
        :param note: the new note to assign to the backtest
        """
        self._api.post("backtests/update", {
            "projectId": project_id,
            "backtestId": backtest_id,
            "name": name,
            "note": note
        })

    def delete(self, project_id: int, backtest_id: str) -> None:
        """Deletes an existing backtest.

        :param project_id: the id of the project the backtest belongs to
        :param backtest_id: the id of the backtest to delete
        """
        self._api.post("backtests/delete", {
            "projectId": project_id,
            "backtestId": backtest_id
        })
