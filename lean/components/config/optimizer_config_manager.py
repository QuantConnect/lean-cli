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

from typing import List, Tuple

from click import prompt, confirm, FLOAT, FloatRange, IntRange

from lean.components.util.logger import Logger
from lean.models.api import QCParameter
from lean.models.logger import Option
from lean.models.optimizer import (OptimizationConstraint, OptimizationConstraintOperator, OptimizationExtremum,
                                   OptimizationParameter, OptimizationTarget)
from lean.models.pydantic import WrappedBaseModel


class NodeType(WrappedBaseModel):
    name: str
    ram: int
    cores: int
    price: float
    min_nodes: int
    max_nodes: int
    default_nodes: int


# The nodes that are available in the cloud
# Copied from ViewsOptimization.NodeTypes in js/views/ViewsOptimization.js
available_nodes = [
    NodeType(name="O2-8",
             ram=8,
             cores=2,
             price=0.15,
             min_nodes=1,
             max_nodes=24,
             default_nodes=12),
    NodeType(name="O4-12",
             ram=12,
             cores=4,
             price=0.3,
             min_nodes=1,
             max_nodes=12,
             default_nodes=6),
    NodeType(name="O8-16",
             ram=16,
             cores=8,
             price=0.6,
             min_nodes=1,
             max_nodes=6,
             default_nodes=3)
]


class OptimizerConfigManager:
    """The OptimizationConfigurer contains methods to interactively configure parts of the optimizer."""

    def __init__(self, logger: Logger) -> None:
        """Creates a new OptimizationConfigurer instance.

        :param logger: the logger to use when printing messages
        """
        self._logger = logger

        # The targets that are available in the cloud
        self.available_targets = [
            ("TotalPerformance.PortfolioStatistics.SharpeRatio", "Sharpe Ratio"),
            ("TotalPerformance.PortfolioStatistics.CompoundingAnnualReturn", "Compounding Annual Return"),
            ("TotalPerformance.PortfolioStatistics.ProbabilisticSharpeRatio", "Probabilistic Sharpe Ratio"),
            ("TotalPerformance.PortfolioStatistics.Drawdown", "Drawdown")
        ]

    def configure_strategy(self, cloud: bool) -> str:
        """Asks the user for the optimization strategy to use.

        :param cloud: True if the optimization will be ran in the cloud, False if not
        :return: the class name of the optimization strategy to use
        """
        options = [
            Option(id="QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy", label="Grid Search")
        ]

        if not cloud:
            options.append(
                Option(id="QuantConnect.Optimizer.Strategies.EulerSearchOptimizationStrategy", label="Euler Search")
            )

        return self._logger.prompt_list("Select the optimization strategy to use", options)

    def configure_target(self) -> OptimizationTarget:
        """Asks the user for the optimization target.

        :return: the chosen optimization target
        """
        from itertools import product
        # Create a list of options containing a "<target> (min)" and "<target> (max)" option for every target
        options = list(product(self.available_targets,
                                         [OptimizationExtremum.Minimum, OptimizationExtremum.Maximum]))
        options = [Option(id=OptimizationTarget(target=option[0][0], extremum=option[1]),
                          label=f"{option[0][1]} ({option[1]})") for option in options]

        return self._logger.prompt_list("Select an optimization target", options)

    def configure_parameters(self, project_parameters: List[QCParameter], cloud: bool) -> List[OptimizationParameter]:
        """Asks the user which parameters need to be optimized and with what constraints.

        :param project_parameters: the parameters of the project that will be optimized
        :param cloud: True if the optimization will be ran in the cloud, False if not
        :return: the chosen optimization parameters
        """
        results: List[OptimizationParameter] = []

        for parameter in project_parameters:
            if cloud and len(results) == 2:
                self._logger.warn(f"You can optimize up to 2 parameters in the cloud, skipping '{parameter.key}'")
                continue

            if not confirm(f"Should the '{parameter.key}' parameter be optimized?", default=True):
                continue

            minimum = prompt(f"Minimum value for '{parameter.key}'", type=FLOAT)
            maximum = prompt(f"Maximum value for '{parameter.key}'", type=FloatRange(min=minimum))
            step_size = prompt(f"Step size for '{parameter.key}'", type=FloatRange(min=0.0), default=1.0)

            results.append(OptimizationParameter(name=parameter.key, min=minimum, max=maximum, step=step_size))

        return results

    def configure_constraints(self) -> List[OptimizationConstraint]:
        """Asks the user for the optimization constraints.

        :return: the chosen optimization constraints
        """
        self._logger.info("Constraints can be used to filter out backtests from the results")
        self._logger.info("When a backtest doesn't comply with the constraints it is dropped from the results")
        self._logger.info("Example constraint: Drawdown < 0.25 (Drawdown less than 25%)")

        results: List[OptimizationConstraint] = []

        while True:
            results_str = ", ".join([str(result) for result in results])
            results_str = results_str or "None"
            self._logger.info(f"Current constraints: {results_str}")

            if not confirm("Do you want to add a constraint?", default=False):
                return results

            target_options = [Option(id=target[0], label=target[1]) for target in self.available_targets]
            target = self._logger.prompt_list("Select a constraint target", target_options)

            operator = self._logger.prompt_list("Select a constraint operator (<value> will be asked after this)", [
                Option(id=OptimizationConstraintOperator.Less, label="Less than <value>"),
                Option(id=OptimizationConstraintOperator.LessOrEqual, label="Less than or equal to <value>"),
                Option(id=OptimizationConstraintOperator.Greater, label="Greater than <value>"),
                Option(id=OptimizationConstraintOperator.GreaterOrEqual, label="Greater than or equal to <value>"),
                Option(id=OptimizationConstraintOperator.Equals, label="Equal to <value>"),
                Option(id=OptimizationConstraintOperator.NotEqual, label="Not equal to <value>")
            ])

            value = prompt("Set the <value> for the selected operator", type=FLOAT)

            results.append(OptimizationConstraint(**{"target": target, "operator": operator, "target-value": value}))

    def configure_node(self) -> Tuple[NodeType, int]:
        """Asks the user for the node type and number of parallel nodes to run on.

        :return: the type of the node and the amount of parallel nodes to run
        """
        node_options = [
            Option(id=node, label=f"{node.name} ({node.cores} cores, {node.ram} GB RAM) @ ${node.price:.2f} per hour")
            for node in available_nodes
        ]

        node = self._logger.prompt_list("Select the optimization node type", node_options)
        parallel_nodes = prompt(f"How many nodes should run in parallel ({node.min_nodes}-{node.max_nodes})",
                                      type=IntRange(min=node.min_nodes, max=node.max_nodes),
                                      default=node.default_nodes)

        return node, parallel_nodes

    def parse_target(self, target: str) -> str:
        """Parses a target given by the user.

        Converts a target like "Sharpe Ratio" into "TotalPerformance.PortfolioStatistics.SharpeRatio".

        :param target: the target given by the user
        :return: the target in a way it can be passed to the optimizer
        """
        if "." in target:
            return target
        from re import sub

        # Turn "SharpeRatio" into "Sharpe Ratio" so the title() call doesn't lowercase the R
        target = sub(r"([A-Z])", r" \1", target)

        return f"TotalPerformance.PortfolioStatistics.{target.title().replace(' ', '')}"

    def parse_parameters(self, parameters: List[Tuple[str, float, float, float]]) -> List[OptimizationParameter]:
        """Parses a list of parameters given by the user into a list of parameter objects.

        :param parameters: the parameters given by the user
        :return: the parameters the user gave as OptimizationParameter objects
        """
        parsed_parameters = []

        for name, minimum, maximum, step in parameters:
            parsed_parameters.append(OptimizationParameter(name=name, min=minimum, max=maximum, step=step))

        return parsed_parameters

    def parse_constraints(self, constraints: List[str]) -> List[OptimizationConstraint]:
        """Parses a list of constraints given by the user into a list of constraint objects.

        :param constraints: the constraints given by the user
        :return: the constraints the user gave as OptimizationConstraint objects
        """
        parsed_constraints = []

        for constraint in constraints:
            parts = constraint.rsplit(" ", 2)

            operator = {
                ">": OptimizationConstraintOperator.Greater,
                "<": OptimizationConstraintOperator.Less,
                ">=": OptimizationConstraintOperator.GreaterOrEqual,
                "<=": OptimizationConstraintOperator.LessOrEqual,
                "==": OptimizationConstraintOperator.Equals,
                "!=": OptimizationConstraintOperator.NotEqual
            }[parts[1]]

            parsed_constraints.append(OptimizationConstraint(**{"target": self.parse_target(parts[0]),
                                                                "operator": operator,
                                                                "target-value": float(parts[2])}))

        return parsed_constraints
