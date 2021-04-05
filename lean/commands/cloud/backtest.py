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

import webbrowser
from typing import Optional

import click

from lean.click import LeanCommand
from lean.container import container


@click.command(cls=LeanCommand)
@click.argument("project", type=str)
@click.option("--name", type=str, help="The name of the backtest (a random one is generated if not specified)")
@click.option("--push",
              is_flag=True,
              default=False,
              help="Push local modifications to the cloud before running the backtest")
@click.option("--open", "open_browser",
              is_flag=True,
              default=False,
              help="Automatically open the results in the browser when the backtest is finished")
def backtest(project: str, name: Optional[str], push: bool, open_browser: bool) -> None:
    """Backtest a project in the cloud.

    PROJECT must be the name or id of the project to run a backtest for.

    If the project that has to be backtested has been pulled to the local drive
    with `lean cloud pull` it is possible to use the --push option to push local
    modifications to the cloud before running the backtest.
    """
    logger = container.logger()

    cloud_project_manager = container.cloud_project_manager()
    cloud_project = cloud_project_manager.get_cloud_project(project, push)

    if name is None:
        name = container.name_generator().generate_name()

    cloud_runner = container.cloud_runner()
    finished_backtest = cloud_runner.run_backtest(cloud_project, name)

    if finished_backtest.error is None and finished_backtest.stacktrace is None:
        logger.info(finished_backtest.get_statistics_table())

    logger.info(f"Backtest id: {finished_backtest.backtestId}")
    logger.info(f"Backtest name: {finished_backtest.name}")
    logger.info(f"Backtest url: {finished_backtest.get_url()}")

    if finished_backtest.error is not None or finished_backtest.stacktrace is not None:
        error = finished_backtest.stacktrace or finished_backtest.error
        error = error.strip()

        logger.error("An error occurred during this backtest:")
        logger.error(error)

        # Don't open the results in the browser if the error happened during initialization
        # In the browser the logs won't show these errors, you'll just get empty charts and empty logs
        if error.startswith("During the algorithm initialization, the following exception has occurred:"):
            open_browser = False

    if open_browser:
        webbrowser.open(finished_backtest.get_url())
