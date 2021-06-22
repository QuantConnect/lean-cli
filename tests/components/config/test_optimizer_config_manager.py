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

from unittest import mock

import pytest

from lean.components.config.optimizer_config_manager import OptimizerConfigManager
from lean.models.optimizer import OptimizationConstraintOperator


@pytest.mark.parametrize("given_target,output", [
    ("TotalPerformance.PortfolioStatistics.Drawdown", "TotalPerformance.PortfolioStatistics.Drawdown"),
    ("Drawdown", "TotalPerformance.PortfolioStatistics.Drawdown"),
    ("drawdown", "TotalPerformance.PortfolioStatistics.Drawdown"),
    ("TotalPerformance.PortfolioStatistics.SharpeRatio", "TotalPerformance.PortfolioStatistics.SharpeRatio"),
    ("SharpeRatio", "TotalPerformance.PortfolioStatistics.SharpeRatio"),
    ("Sharpe Ratio", "TotalPerformance.PortfolioStatistics.SharpeRatio"),
    ("Sharpe ratio", "TotalPerformance.PortfolioStatistics.SharpeRatio"),
    ("sharpe ratio", "TotalPerformance.PortfolioStatistics.SharpeRatio"),
])
def test_parse_target_parses_correctly(given_target: str, output: str) -> None:
    optimizer_config_manager = OptimizerConfigManager(mock.Mock())

    assert optimizer_config_manager.parse_target(given_target) == output


def test_parse_parameters_parses_correctly() -> None:
    optimizer_config_manager = OptimizerConfigManager(mock.Mock())

    parameters = optimizer_config_manager.parse_parameters([
        ("my-first-parameter", 1, 10, 0.5),
        ("my-second-parameter", 20, 30, 5)
    ])

    assert len(parameters) == 2

    assert parameters[0].name == "my-first-parameter"
    assert parameters[0].min == 1
    assert parameters[0].max == 10
    assert parameters[0].step == 0.5

    assert parameters[1].name == "my-second-parameter"
    assert parameters[1].min == 20
    assert parameters[1].max == 30
    assert parameters[1].step == 5


@pytest.mark.parametrize("given_constraint,expected_target,expected_operator,expected_value", [
    ("TotalPerformance.PortfolioStatistics.SharpeRatio > 0.1",
     "TotalPerformance.PortfolioStatistics.SharpeRatio",
     OptimizationConstraintOperator.Greater,
     0.1),
    ("SharpeRatio < 0.2",
     "TotalPerformance.PortfolioStatistics.SharpeRatio",
     OptimizationConstraintOperator.Less,
     0.2),
    ("Sharpe Ratio >= 0.3",
     "TotalPerformance.PortfolioStatistics.SharpeRatio",
     OptimizationConstraintOperator.GreaterOrEqual,
     0.3),
    ("Sharpe ratio <= 0.4",
     "TotalPerformance.PortfolioStatistics.SharpeRatio",
     OptimizationConstraintOperator.LessOrEqual,
     0.4),
    ("sharpe ratio == 0.5",
     "TotalPerformance.PortfolioStatistics.SharpeRatio",
     OptimizationConstraintOperator.Equals,
     0.5),
    ("Sharpe Ratio != 0.6",
     "TotalPerformance.PortfolioStatistics.SharpeRatio",
     OptimizationConstraintOperator.NotEqual,
     0.6)
])
def test_parse_constraints_parses_correctly(given_constraint: str,
                                            expected_target: str,
                                            expected_operator: OptimizationConstraintOperator,
                                            expected_value: float) -> None:
    optimizer_config_manager = OptimizerConfigManager(mock.Mock())

    constraints = optimizer_config_manager.parse_constraints([given_constraint])

    assert len(constraints) == 1

    assert constraints[0].target == expected_target
    assert constraints[0].operator == expected_operator
    assert constraints[0].target_value == expected_value
