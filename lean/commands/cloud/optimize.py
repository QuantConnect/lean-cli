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
from datetime import timedelta
from math import ceil
from typing import List, Optional

import click

from lean.click import LeanCommand
from lean.container import container
from lean.models.api import QCOptimizationBacktest
from lean.models.optimizer import OptimizationConstraint, OptimizationExtremum, OptimizationParameter


def _calculate_backtest_count(parameters: List[OptimizationParameter]) -> int:
    """Calculates the number of backtests needed for the given optimization parameters.

    :param parameters: the parameters to optimize
    :return: the number of backtests a grid search on the parameters would require
    """
    steps_per_parameter = [round((p.max - p.min) / p.step) + 1 for p in parameters]
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


def _get_backtest_statistic(backtest: QCOptimizationBacktest, target: str) -> float:
    """Returns a statistic of a backtest.

    :param backtest: the backtest to retrieve the statistic from
    :param target: the target statistic to retrieve, must be one of OptimizerConfigManager.available_targets
    :return: the value of the target statistic on the backtest
    """
    if target == "TotalPerformance.PortfolioStatistics.SharpeRatio":
        return backtest.statistics[14]
    elif target == "TotalPerformance.PortfolioStatistics.CompoundingAnnualReturn":
        return backtest.statistics[6]
    elif target == "TotalPerformance.PortfolioStatistics.ProbabilisticSharpeRatio":
        return backtest.statistics[12]
    elif target == "TotalPerformance.PortfolioStatistics.Drawdown":
        return backtest.statistics[7]
    else:
        raise ValueError(f"Target is not supported: {target}")


def _backtest_meets_constraints(backtest: QCOptimizationBacktest, constraints: List[OptimizationConstraint]) -> bool:
    """Returns whether the backtest meets all constraints.

    :param backtest: the backtest to check
    :param constraints: the constraints the backtest has to meet
    :return: True if the backtest meets all constraints, False if not
    """
    optimizer_config_manager = container.optimizer_config_manager()

    for constraint in constraints:
        expression = str(constraint)

        for target, _ in optimizer_config_manager.available_targets:
            expression = expression.replace(target, str(_get_backtest_statistic(backtest, target)))

        if not eval(expression):
            return False

    return True


@click.command(cls=LeanCommand)
@click.argument("project", type=str)
@click.option("--name", type=str, help="The name of the optimization (a random one is generated if not specified)")
@click.option("--push",
              is_flag=True,
              default=False,
              help="Push local modifications to the cloud before starting the optimization")
def optimize(project: str, name: Optional[str], push: bool) -> None:
    """Optimize a project in the cloud.

    An interactive prompt will be shown to configure the optimizer.

    PROJECT must be the name or id of the project to optimize.

    If the project that has to be optimized has been pulled to the local drive
    with `lean cloud pull` it is possible to use the --push option to push local
    modifications to the cloud before running the optimization.
    """
    logger = container.logger()
    api_client = container.api_client()

    cloud_project_manager = container.cloud_project_manager()
    cloud_project = cloud_project_manager.get_cloud_project(project, push)

    if name is None:
        name = container.name_generator().generate_name()

    cloud_runner = container.cloud_runner()
    finished_compile = cloud_runner.compile_project(cloud_project)

    optimizer_config_manager = container.optimizer_config_manager()
    optimization_strategy = optimizer_config_manager.configure_strategy(cloud=True)
    optimization_target = optimizer_config_manager.configure_target()
    optimization_parameters = optimizer_config_manager.configure_parameters(cloud_project.parameters, cloud=True)
    optimization_constraints = optimizer_config_manager.configure_constraints()

    backtest_count = _calculate_backtest_count(optimization_parameters)

    organization = api_client.organizations.get(cloud_project.organizationId)

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

        logger.info(f"Estimated number of backtests: {backtest_count:,}")
        logger.info(f"Estimated batch time: {_format_hours(batch_time)}")
        logger.info(f"Estimated batch cost: ${batch_cost:,.2f}")
        logger.info(
            f"Organization balance: {organization.credit.balance:,.0f} QCC (${organization.credit.balance / 100:,.2f})")

        if click.confirm("Do you want to start the optimization on the selected node type?", default=True):
            break

    optimization = cloud_runner.run_optimization(cloud_project,
                                                 finished_compile,
                                                 name,
                                                 optimization_strategy,
                                                 optimization_target,
                                                 optimization_parameters,
                                                 optimization_constraints,
                                                 node.name,
                                                 parallel_nodes)

    backtests = optimization.backtests.values()
    backtests = [b for b in backtests if b.exitCode == 0]
    backtests = [b for b in backtests if
                 _backtest_meets_constraints(b, optimization_constraints)]

    if len(backtests) == 0:
        logger.info("No optimal parameter combination found, no successful backtests meet all constraints")
        return

    optimal_backtest = sorted(backtests,
                              key=lambda backtest: _get_backtest_statistic(backtest, optimization_target.target),
                              reverse=optimization_target.extremum == OptimizationExtremum.Maximum)[0]

    parameters = ", ".join(f"{key}: {optimal_backtest.parameterSet[key]}" for key in optimal_backtest.parameterSet)
    logger.info(f"Optimal parameters: {parameters}")

    optimal_backtest = api_client.backtests.get(cloud_project.projectId,
                                                optimal_backtest.id)

    logger.info(f"Optimal backtest id: {optimal_backtest.backtestId}")
    logger.info(f"Optimal backtest name: {optimal_backtest.name}")
    logger.info(f"Optimal backtest results:")
    logger.info(optimal_backtest.get_statistics_table())
