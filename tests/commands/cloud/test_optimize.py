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
from click.testing import CliRunner

from lean.commands import lean
from lean.components.config.optimizer_config_manager import NodeType, OptimizerConfigManager
from lean.container import container
from lean.models.api import QCOptimization, QCOptimizationBacktest, QCOptimizationEstimate
from lean.models.optimizer import (OptimizationConstraint, OptimizationExtremum, OptimizationParameter,
                                   OptimizationTarget)
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory, create_api_organization
from tests.conftest import initialize_container


def create_api_optimization() -> QCOptimization:
    return QCOptimization(optimizationId="123",
                          projectId=1,
                          status="completed",
                          name="Optimization name",
                          backtests={},
                          runtimeStatistics={})


def create_api_optimization_backtest(id: int,
                                     success: bool,
                                     meets_constraints: bool,
                                     maximize_statistics: bool) -> QCOptimizationBacktest:
    # Drawdown must be less than 0.25 to meet the constraints
    if meets_constraints:
        statistics = [0.24 if maximize_statistics else 0.01] * 30
    else:
        statistics = [1.0] * 30

    return QCOptimizationBacktest(id=str(id),
                                  name=f"Backtest {id}",
                                  exitCode=0 if success else 1,
                                  parameterSet={"id": str(id)},
                                  statistics=statistics)


def _get_optimizer_config_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the optimizer config manager before every test."""
    optimizer_config_manager = mock.Mock()

    optimizer_config_manager.available_targets = OptimizerConfigManager(mock.Mock()).available_targets

    optimizer_config_manager.configure_strategy.return_value = "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy"
    optimizer_config_manager.configure_target.return_value = OptimizationTarget(
        target="TotalPerformance.PortfolioStatistics.SharpeRatio",
        extremum=OptimizationExtremum.Maximum)

    optimizer_config_manager.configure_parameters.return_value = [
        OptimizationParameter(name="param1", min=1.0, max=10.0, step=0.5)
    ]

    optimizer_config_manager.configure_constraints.return_value = [
        OptimizationConstraint(**{"target": "TotalPerformance.PortfolioStatistics.Drawdown",
                                  "operator": "less",
                                  "target-value": "0.25"})
    ]

    optimizer_config_manager.configure_node.return_value = NodeType(name="O8-16",
                                                                    ram=16,
                                                                    cores=8,
                                                                    price=0.6,
                                                                    min_nodes=1,
                                                                    max_nodes=6,
                                                                    default_nodes=3), 3

    return optimizer_config_manager


def test_cloud_optimize_runs_optimization_by_project_id() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "1"])

    assert result.exit_code == 0

    cloud_runner.run_optimization.assert_called_once()
    args, kwargs = cloud_runner.run_optimization.call_args

    assert args[0] == project


def test_cloud_optimize_runs_optimization_by_project_name() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=1000, balance=10)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project"])

    assert result.exit_code == 0

    cloud_runner.run_optimization.assert_called_once()
    args, kwargs = cloud_runner.run_optimization.call_args

    assert args[0] == project


def test_cloud_optimize_uses_given_name() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization

    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project", "--name", "My Name"])

    assert result.exit_code == 0

    cloud_runner.run_optimization.assert_called_once()
    args, kwargs = cloud_runner.run_optimization.call_args

    assert args[2] == "My Name"


def test_cloud_optimize_pushes_nothing_when_project_does_not_exist_locally() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization

    push_manager = mock.MagicMock()
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client,
                         push_manager_to_use=push_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project", "--push"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_not_called()


def test_cloud_optimize_passes_given_config_to_cloud_runner() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project", "--name", "My Name"])

    assert result.exit_code == 0

    optimizer_config_manager = container.optimizer_config_manager
    cloud_runner.run_optimization.assert_called_once_with(project,
                                                          mock.ANY,
                                                          "My Name",
                                                          optimizer_config_manager.configure_strategy(cloud=True),
                                                          optimizer_config_manager.configure_target(),
                                                          optimizer_config_manager.configure_parameters([]),
                                                          optimizer_config_manager.configure_constraints(),
                                                          optimizer_config_manager.configure_node()[0].name,
                                                          optimizer_config_manager.configure_node()[1])


@pytest.mark.parametrize("target,extremum", [("SharpeRatio", OptimizationExtremum.Minimum),
                                             ("SharpeRatio", OptimizationExtremum.Maximum),
                                             ("CompoundingAnnualReturn", OptimizationExtremum.Minimum),
                                             ("CompoundingAnnualReturn", OptimizationExtremum.Maximum),
                                             ("ProbabilisticSharpeRatio", OptimizationExtremum.Minimum),
                                             ("ProbabilisticSharpeRatio", OptimizationExtremum.Maximum),
                                             ("Drawdown", OptimizationExtremum.Minimum),
                                             ("Drawdown", OptimizationExtremum.Maximum)])
def test_cloud_optimize_displays_optimal_backtest_results(target: str,
                                                          extremum: OptimizationExtremum) -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()
    optimization.backtests["1"] = create_api_optimization_backtest(1, True, True, True)
    optimization.backtests["2"] = create_api_optimization_backtest(2, True, True, False)

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    container.optimizer_config_manager.configure_target.return_value = OptimizationTarget(
        target=f"TotalPerformance.PortfolioStatistics.{target}",
        extremum=extremum,
    )

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project"])

    assert result.exit_code == 0

    if extremum == OptimizationExtremum.Maximum:
        assert "id: 1" in result.output
    else:
        assert "id: 2" in result.output


def test_cloud_optimize_does_not_display_backtest_results_when_none_succeed() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()
    optimization.backtests["1"] = create_api_optimization_backtest(1, False, True, True)
    optimization.backtests["2"] = create_api_optimization_backtest(2, False, True, False)

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project"])

    assert result.exit_code == 0

    assert "id: 1" not in result.output
    assert "id: 2" not in result.output


def test_cloud_optimize_does_not_display_backtest_results_when_none_meet_constraints() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()
    optimization.backtests["1"] = create_api_optimization_backtest(1, True, False, True)
    optimization.backtests["2"] = create_api_optimization_backtest(2, True, False, False)

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project"])

    assert result.exit_code == 0

    assert "id: 1" not in result.output
    assert "id: 2" not in result.output


def test_cloud_optimize_aborts_when_optimization_fails() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")

    def run_optimization(*args, **kwargs):
        raise RuntimeError("Oops")

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.side_effect = run_optimization
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "My Project"])

    assert result.exit_code != 0

    cloud_runner.run_optimization.assert_called_once()


def test_cloud_optimize_aborts_when_input_matches_no_cloud_project() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    optimization = create_api_optimization()

    api_client = mock.MagicMock()
    api_client.projects.get_all.return_value = [project]
    api_client.optimizations.estimate.return_value = QCOptimizationEstimate(estimateId="x", time=10, balance=1000)
    api_client.organizations.get.return_value = create_api_organization()

    cloud_runner = mock.MagicMock()
    cloud_runner.run_optimization.return_value = optimization
    container = initialize_container(cloud_runner_to_use=cloud_runner, api_client_to_use=api_client)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["cloud", "optimize", "Fake Project"])

    assert result.exit_code != 0

    cloud_runner.run_optimization.assert_not_called()
