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

from click import confirm

from lean.components.api.api_client import APIClient
from lean.components.util.logger import Logger
from lean.components.util.task_manager import TaskManager
from lean.models.api import QCBacktest, QCCompileState, QCCompileWithLogs, QCOptimization, QCProject
from lean.models.errors import RequestFailedError
from lean.models.optimizer import OptimizationConstraint, OptimizationParameter, OptimizationTarget


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
        self._mismatch_counter = 0

    def is_backtest_done(self, backtest_data: QCBacktest, delay: float = 10.0):
        """Checks if the backtest is complete.

        :param backtest_data: The current state of the backtest.
        :param delay: The delay in seconds between consecutive checks. Default is 60 seconds (1 minute).
        :return: True if the backtest is complete and the state has changed, False otherwise.
        """
        try:
            if backtest_data.error or backtest_data.stacktrace:
                self._mismatch_counter = 0
                return True

            is_complete = backtest_data.is_complete()
            self._logger.debug(f"[Backtest ID: {backtest_data.backtestId}] Completion status: {is_complete}")

            if is_complete:
                if backtest_data.totalPerformance:
                    self._mismatch_counter = 0
                    return True

                if self._mismatch_counter >= 6:
                    self._logger.error(f"[Backtest ID: {backtest_data.backtestId}] We could not retrieve "
                                       f"the complete backtest results, please try again later.")
                    self._mismatch_counter = 0
                    return True

                self._mismatch_counter += 1
                self._logger.debug(f"[Backtest ID: {backtest_data.backtestId}] Incremented mismatch counter to "
                                   f"{self._mismatch_counter}. Will re-check after {delay} seconds.")
                import time
                time.sleep(delay)

            return False
        except Exception as e:
            self._logger.error(f"Error checking backtest completion status for ID {backtest_data.backtestId}: {e}")
            raise

    def run_backtest(self, project: QCProject, name: str) -> QCBacktest:
        """Runs a backtest in the cloud.

        :param project: the project to backtest
        :param name: the name of the backtest
        :return: the completed backtest
        """
        finished_compile = self.compile_project(project)
        created_backtest = self._api_client.backtests.create(project.projectId, finished_compile.compileId, name)

        self._logger.info(f"Started backtest named '{name}' for project '{project.name}'")
        self._logger.info(f"Backtest url: {created_backtest.get_url()}")

        try:
            return self._task_manager.poll(
                make_request=lambda: self._api_client.backtests.get(project.projectId, created_backtest.backtestId),
                is_done=self.is_backtest_done,
                get_progress=lambda data: data.progress
            )
        except KeyboardInterrupt as e:
            if confirm("Do you want to cancel and delete the running backtest?", True):
                self._api_client.backtests.delete(project.projectId, created_backtest.backtestId)
                self._logger.info(f"Successfully cancelled and deleted backtest '{name}'")
            raise e

    def run_optimization(self,
                         project: QCProject,
                         finished_compile: QCCompileWithLogs,
                         name: str,
                         strategy: str,
                         target: OptimizationTarget,
                         parameters: List[OptimizationParameter],
                         constraints: List[OptimizationConstraint],
                         node_type: str,
                         parallel_nodes: int) -> QCOptimization:
        """Runs an optimization in the cloud.

        :param project: the project to optimize
        :param finished_compile: a finished compile of the given project
        :param name: the name of the optimization
        :param strategy: the strategy to optimize with
        :param target: the target of the optimization
        :param parameters: the parameters to optimize
        :param constraints: the constraints of the optimization
        :param node_type: the type of the node to run the optimization on
        :param parallel_nodes: the number of parallel nodes to run the optimization on
        :return: the completed optimization
        """
        created_optimization = self._api_client.optimizations.create(project.projectId,
                                                                     finished_compile.compileId,
                                                                     name,
                                                                     strategy,
                                                                     target,
                                                                     parameters,
                                                                     constraints,
                                                                     node_type,
                                                                     parallel_nodes)

        self._logger.info(f"Started optimization named '{name}' for project '{project.name}'")
        self._logger.info(f"Project url: {project.get_url()}")

        try:
            return self._task_manager.poll(
                make_request=lambda: self._api_client.optimizations.get(created_optimization.optimizationId),
                is_done=lambda data: data.status != "active" and data.status != "running" and data.status != "new",
                get_progress=lambda data: data.get_progress()
            )
        except KeyboardInterrupt as e:
            if confirm("Do you want to cancel and delete the running optimization?", True):
                try:
                    self._api_client.optimizations.abort(created_optimization.optimizationId)
                except RequestFailedError:
                    # The optimization finished between the user pressed Ctrl+C and confirmed the deletion
                    pass
                finally:
                    self._api_client.optimizations.delete(created_optimization.optimizationId)
                    self._logger.info(f"Successfully cancelled and deleted optimization '{name}'")
            raise e

    def compile_project(self, project: QCProject) -> QCCompileWithLogs:
        """Compiles a project in the cloud.

        :param project: the project to compile
        :return: a QCCompileWithLogs instance containing the details of the finished compile
        """
        self._logger.info(f"Started compiling project '{project.name}'")

        created_compile = self._api_client.compiles.create(project.projectId)

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
