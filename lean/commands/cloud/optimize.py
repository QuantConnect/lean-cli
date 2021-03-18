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

import functools
import operator
import webbrowser
from datetime import timedelta
from math import ceil
from pathlib import Path
from typing import List, Optional

import click

from lean.click import LeanCommand
from lean.container import container
from lean.models.optimizer import OptimizationParameter


def _calculate_backtest_count(parameters: List[OptimizationParameter]) -> int:
    """Calculates the number of backtests needed for the given optimization parameters.

    :param parameters: the parameters to optimize
    :return: the number of backtests a grid search on the parameters would require
    """
    steps_per_parameter = [(p.max - p.min + 1) / p.step for p in parameters]
    return int(functools.reduce(operator.mul, steps_per_parameter, 1))


def _calculate_hours(backtest_time: int, backtest_count: int) -> float:
    """Calculates the total number of hours the optimization will take, given only one node is used.

    :param backtest_time: the number of seconds one backtest is expected to take
    :param backtest_count: the number of backtests that need to be ran
    """
    deploy_time = 30
    backtest_cpu_factor = 1.5
    seconds = (deploy_time + backtest_time * backtest_cpu_factor) * backtest_count
    hours = ceil((seconds * 100) / 3600) / 100
    return max(0.1, hours)


def _format_hours(hours: float) -> str:
    """Format a certain number of hours to a string.

    If the number of hours is less than 1 this returns "x minutes".
    If the number of hours is greater than or equal to 1 this returns "x hours".

    :param hours: the number of hours
    :return: the formatted number of hours
    """
    seconds = timedelta(hours=hours).total_seconds()

    if seconds < 60 * 60:
        amount = round(seconds / 60)
        unit = "minute"
    else:
        amount = round(seconds / (60 * 60))
        unit = "hour"

    unit_suffix = "s" if amount != 1 else ""
    return f"{amount:,} {unit}{unit_suffix}"


@click.command(cls=LeanCommand)
@click.argument("project", type=str)
@click.option("--name", type=str, help="The name of the optimization (a random one is generated if not specified)")
@click.option("--push",
              is_flag=True,
              default=False,
              help="Push local modifications to the cloud before starting the optimization")
@click.option("--open", "open_browser",
              is_flag=True,
              default=False,
              help="Automatically open the project in the browser when the optimization has started")
def optimize(project: str, name: Optional[str], push: bool, open_browser: bool) -> None:
    """Optimize a project in the cloud.

    PROJECT should be the name or id of a cloud project.

    If the project that has to be optimized has been pulled to the local drive
    with `lean cloud pull` it is possible to use the --push option to push local
    modifications to the cloud before running the optimization.
    """
    logger = container.logger()

    api_client = container.api_client()
    all_projects = api_client.projects.get_all()

    for p in all_projects:
        if str(p.projectId) == project or p.name == project:
            cloud_project = p
            break
    else:
        raise RuntimeError("No project with the given name or id exists in the cloud")

    if push:
        local_path = Path.cwd() / cloud_project.name
        if local_path.exists():
            push_manager = container.push_manager()
            push_manager.push_projects([local_path])
        else:
            logger.info(f"'{cloud_project.name}' does not exist locally, not pushing anything")

    if name is None:
        name = container.name_generator().generate_name()

    cloud_runner = container.cloud_runner()
    finished_compile = cloud_runner.compile_project(cloud_project)

    optimizer_config_manager = container.optimizer_config_manager()
    optimization_strategy = optimizer_config_manager.configure_strategy(cloud=True)
    optimization_target = optimizer_config_manager.configure_target()
    optimization_parameters = optimizer_config_manager.configure_parameters(cloud_project.parameters)
    optimization_constraints = optimizer_config_manager.configure_constraints()

    backtest_count = _calculate_backtest_count(optimization_parameters)

    while True:
        node, parallel_nodes = optimizer_config_manager.configure_node()

        estimate = api_client.optimizations.estimate(cloud_project.projectId,
                                                     finished_compile.compileId,
                                                     name,
                                                     optimization_strategy,
                                                     optimization_target,
                                                     optimization_parameters,
                                                     optimization_constraints,
                                                     node.name,
                                                     parallel_nodes)

        hours = _calculate_hours(estimate.time, backtest_count)
        batch_time = ceil((hours * 100) / parallel_nodes) / 100
        batch_cost = max(0.01, ceil(node.price * hours * 100) / 100)

        print(f"Estimated number of backtests: {backtest_count:,}")
        print(f"Estimated batch time: {_format_hours(batch_time)}")
        print(f"Estimated batch cost: ${batch_cost:,.2f}")

        if click.confirm("Do you want to start the optimization on the selected node type?", default=True):
            break

    cloud_runner.run_optimization(cloud_project,
                                  finished_compile,
                                  name,
                                  optimization_strategy,
                                  optimization_target,
                                  optimization_parameters,
                                  optimization_constraints,
                                  node.name,
                                  parallel_nodes)

    if open_browser:
        webbrowser.open(cloud_project.get_url())
