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

import click

from lean.components.api.api_client import APIClient
from lean.components.util.logger import Logger
from lean.components.util.task_manager import TaskManager
from lean.models.api import QCBacktest, QCCompileState, QCCompileWithLogs, QCProject


class CloudRunner:
    """The CloudRunner is responsible for running projects in the cloud."""

    def __init__(self, logger: Logger, api_client: APIClient, task_manager: TaskManager):
        """Creates a new CloudBacktestRunner instance.

        :param logger: the logger to use to log messages with
        :param api_client: the APIClient instance to use when communicating with the QuantConnect API
        :param task_manager: the TaskManager to run long-running tasks with
        """
        self._logger = logger
        self._api_client = api_client
        self._task_manager = task_manager

    def run_backtest(self, project: QCProject, name: str) -> QCBacktest:
        finished_compile = self._compile_project(project)
        created_backtest = self._api_client.backtests.create(project.projectId, finished_compile.compileId, name)

        self._logger.info(f"Started backtest named '{name}' for project '{project.name}'")
        self._logger.info(f"Backtest url: {created_backtest.get_url()}")

        try:
            return self._task_manager.poll(
                make_request=lambda: self._api_client.backtests.get(project.projectId, created_backtest.backtestId),
                is_done=lambda data: data.is_complete(),
                get_progress=lambda data: data.progress
            )
        except KeyboardInterrupt as e:
            if click.confirm("Do you want to cancel and delete the running backtest?", True):
                self._api_client.backtests.delete(project.projectId, created_backtest.backtestId)
                self._logger.info(f"Successfully cancelled and deleted backtest '{name}'")
            raise e

    def _compile_project(self, project: QCProject) -> QCCompileWithLogs:
        """Compiles a project in the cloud.

        :param project: the project to compile
        :return: a QCCompileWithLogs instance containing the details of the finished compile
        """
        self._logger.info(f"Started compiling project '{project.name}'")

        created_compile = self._api_client.compiles.create(project.projectId)

        # Log the parameters reported in the compile
        parameters = []
        parameter_count = 0

        for parameter_container in created_compile.parameters:
            for parameter in parameter_container.parameters:
                parameters.append(f"- {parameter_container.file}:{parameter.line} :: {parameter.type}")
                parameter_count += int(parameter.type.split(" ")[0])

        if parameter_count > 0:
            self._logger.info(f"Detected parameters ({parameter_count}):")
            for parameter in parameters:
                self._logger.info(parameter)
        else:
            self._logger.info("Detected parameters: none")

        finished_compile = self._task_manager.poll(
            make_request=lambda: self._api_client.compiles.get(project.projectId, created_compile.compileId),
            is_done=lambda data: data.state in [QCCompileState.BuildSuccess, QCCompileState.BuildError]
        )

        if finished_compile.state == QCCompileState.BuildError:
            self._logger.error("\n".join(finished_compile.logs))
            raise RuntimeError(f"Something went wrong while compiling project '{project.name}'")

        self._logger.info("\n".join(finished_compile.logs))
        self._logger.info(f"Successfully compiled project '{project.name}'")

        return finished_compile
