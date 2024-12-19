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

from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime, timedelta

from click import command, argument, option, Choice, IntRange

from lean.click import LeanCommand, PathParameter, ensure_options
from lean.components.docker.lean_runner import LeanRunner
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.api import QCParameter, QCBacktest
from lean.models.click_options import options_from_json, get_configs_for_options
from lean.models.cli import cli_data_downloaders, cli_addon_modules
from lean.models.errors import MoreInfoError
from lean.models.optimizer import OptimizationTarget
from lean.components.util.json_modules_handler import build_and_configure_modules, non_interactive_config_build_for_name


def _get_latest_backtest_runtime(algorithm_directory: Path) -> timedelta:
    from re import findall
    from dateutil.parser import isoparse

    missing_backtest_error = RuntimeError(
        "Please run at least one backtest for this project in order to run an optimization estimate");
    backtests_directory = algorithm_directory / "backtests"

    if not backtests_directory.exists():
        raise missing_backtest_error

    def is_backtest_output_directory(path: Path) -> bool:
        try:
            datetime.strptime(path.name, "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            return False
        else:
            return path.is_dir()

    def get_filename_timestamp(path: Path) -> datetime:
        return datetime.strptime(path.name, "%Y-%m-%d_%H-%M-%S")

    backtests_directories = [f for f in backtests_directory.iterdir() if is_backtest_output_directory(f)]
    latest_backtest_directory = max(backtests_directories, key=get_filename_timestamp, default=None)

    if latest_backtest_directory is None:
        raise missing_backtest_error

    latest_backtest_log_file = latest_backtest_directory / "log.txt"

    if not latest_backtest_log_file.exists():
        raise missing_backtest_error

    latest_backtest_logs = latest_backtest_log_file.read_text(encoding="utf-8")
    timestamps = findall(r"(.+) TRACE:: .*\n", latest_backtest_logs)

    return isoparse(timestamps[-1]) - isoparse(timestamps[0])


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/optimizations/TIMESTAMP)")
@option("--detach", "-d",
              is_flag=True,
              default=False,
              help="Run the optimization in a detached Docker container and return immediately")
@option("--optimizer-config",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              help=f"The optimizer configuration file that should be used")
@option("--strategy",
              type=Choice(["Grid Search", "Euler Search"], case_sensitive=False),
              help="The optimization strategy to use")
@option("--target",
              type=str,
              help="The target statistic of the optimization")
@option("--target-direction",
              type=Choice(["min", "max"], case_sensitive=False),
              help="Whether the target must be minimized or maximized")
@option("--parameter",
              type=(str, float, float, float),
              multiple=True,
              help="The 'parameter min max step' pairs configuring the parameters to optimize")
@option("--constraint",
              type=str,
              multiple=True,
              help="The 'statistic operator value' pairs configuring the constraints of the optimization")
@option("--data-provider-historical",
              type=Choice([dp.get_name() for dp in cli_data_downloaders], case_sensitive=False),
              default="Local",
              help="Update the Lean configuration file to retrieve data from the given historical provider")
@option("--download-data",
              is_flag=True,
              default=False,
              help="Update the Lean configuration file to download data from the QuantConnect API, alias for --data-provider-historical QuantConnect")
@option("--data-purchase-limit",
              type=int,
              help="The maximum amount of QCC to spend on downloading data during the backtest when using QuantConnect as historical data provider")
@option("--release",
              is_flag=True,
              default=False,
              help="Compile C# projects in release configuration instead of debug")
@option("--image",
              type=str,
              help=f"The LEAN engine image to use (defaults to {DEFAULT_ENGINE_IMAGE})")
@option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN engine image before running the optimizer")
@option("--estimate",
              is_flag=True,
              default=False,
              help="Estimate optimization runtime without running it")
@option("--max-concurrent-backtests",
              type=IntRange(min=1),
              help="Maximum number of concurrent backtests to run")
@option("--addon-module",
              type=str,
              multiple=True,
              hidden=True)
@option("--extra-config",
              type=(str, str),
              multiple=True,
              hidden=True)
@option("--extra-docker-config",
              type=str,
              default="{}",
              help="Extra docker configuration as a JSON string. "
                   "For more information https://docker-py.readthedocs.io/en/stable/containers.html")
@option("--no-update",
              is_flag=True,
              default=False,
              help="Use the local LEAN engine image instead of pulling the latest version")
@options_from_json(get_configs_for_options("backtest"))
def optimize(project: Path,
             output: Optional[Path],
             detach: bool,
             optimizer_config: Optional[Path],
             strategy: Optional[str],
             target: Optional[str],
             target_direction: Optional[str],
             parameter: List[Tuple[str, float, float, float]],
             constraint: List[str],
             data_provider_historical: Optional[str],
             download_data: bool,
             data_purchase_limit: Optional[int],
             release: bool,
             image: Optional[str],
             update: bool,
             estimate: bool,
             max_concurrent_backtests: Optional[int],
             addon_module: Optional[List[str]],
             extra_config: Optional[Tuple[str, str]],
             extra_docker_config: Optional[str],
             no_update: bool,
             **kwargs) -> None:
    """Optimize a project's parameters locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    By default an interactive wizard is shown letting you configure the optimizer.
    If --optimizer-config or --strategy is given the command runs in non-interactive mode.
    In this mode the CLI does not prompt for input.

    \b
    The --optimizer-config option can be used to specify the configuration to run the optimizer with.
    When using the option it should point to a file like this (the algorithm-* properties should be omitted):
    https://github.com/QuantConnect/Lean/blob/master/Optimizer.Launcher/config.json

    If --strategy is given the optimizer configuration is read from the given options.
    In this case --strategy, --target, --target-direction and --parameter become required.

    \b
    In non-interactive mode the --parameter option can be provided multiple times to configure multiple parameters:
    - --parameter <name> <min value> <max value> <step size>
    - --parameter my-first-parameter 1 10 0.5 --parameter my-second-parameter 20 30 5

    \b
    In non-interactive mode the --constraint option can be provided multiple times to configure multiple constraints:
    - --constraint "<statistic> <operator> <value>"
    - --constraint "Sharpe Ratio >= 0.5" --constraint "Drawdown < 0.25"

    \b
    If --estimate is given, the optimization will not be executed.
    The runtime estimate for the optimization will be calculated and outputted.

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    from json import dumps
    from json5 import loads
    from docker.types import Mount
    from re import findall, search
    from os import cpu_count
    from math import floor

    should_detach = detach and not estimate
    environment_name = "backtesting"
    project_manager = container.project_manager
    algorithm_file = project_manager.find_algorithm_file(project)

    latest_backtest_runtime = timedelta(0)
    if estimate:
        latest_backtest_runtime = _get_latest_backtest_runtime(algorithm_file.parent)

    if output is None:
        output = algorithm_file.parent / "optimizations" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    optimizer_config_manager = container.optimizer_config_manager
    config = None

    if optimizer_config is not None and strategy is not None:
        raise RuntimeError("--optimizer-config and --strategy are mutually exclusive")

    engine_image, container_module_version, project_config = container.manage_docker_image(image, update, no_update,
                                                                                           algorithm_file.parent)
    if optimizer_config is not None:
        config = loads(optimizer_config.read_text(encoding="utf-8"))

        # Remove keys which are configured in the Lean config
        for key in ["algorithm-type-name", "algorithm-language", "algorithm-location"]:
            config.pop(key, None)
    elif strategy is not None:
        ensure_options(["strategy", "target", "target_direction", "parameter"])

        optimization_strategy = f"QuantConnect.Optimizer.Strategies.{strategy.replace(' ', '')}OptimizationStrategy"
        optimization_target = OptimizationTarget(target=optimizer_config_manager.parse_target(target),
                                                 extremum=target_direction)
        optimization_parameters = optimizer_config_manager.parse_parameters(parameter)
        optimization_constraints = optimizer_config_manager.parse_constraints(constraint)
    else:
        project_parameters = [QCParameter(key=k, value=v) for k, v in project_config.get("parameters", {}).items()]

        if len(project_parameters) == 0:
            raise MoreInfoError("The given project has no parameters to optimize",
                                "https://www.lean.io/docs/v2/lean-cli/optimization/parameters")

        optimization_strategy = optimizer_config_manager.configure_strategy(cloud=False)
        optimization_target = optimizer_config_manager.configure_target()
        optimization_parameters = optimizer_config_manager.configure_parameters(project_parameters, cloud=False)
        optimization_constraints = optimizer_config_manager.configure_constraints()

    if config is None:
        # noinspection PyUnboundLocalVariable
        config = {
            "optimization-strategy": optimization_strategy,
            "optimization-strategy-settings": {
                "$type": "QuantConnect.Optimizer.Strategies.StepBaseOptimizationStrategySettings, QuantConnect.Optimizer",
                "default-segment-amount": 10
            },
            "optimization-criterion": {
                "target": optimization_target.target,
                "extremum": optimization_target.extremum.value
            },
            "parameters": [parameter.dict() for parameter in optimization_parameters],
            "constraints": [constraint.dict(by_alias=True) for constraint in optimization_constraints]
        }

    if max_concurrent_backtests is not None:
        config["maximum-concurrent-backtests"] = max_concurrent_backtests
    elif "maximum-concurrent-backtests" in config:
        max_concurrent_backtests = config["maximum-concurrent-backtests"]
    else:
        max_concurrent_backtests = max(1, floor(cpu_count() / 2))

    config["optimizer-close-automatically"] = True
    config["results-destination-folder"] = "/Results"

    config_path = output / "optimizer-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w+", encoding="utf-8") as file:
        file.write(dumps(config, indent=4) + "\n")

    logger = container.logger

    lean_config_manager = container.lean_config_manager
    lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)

    organization_id = container.organization_manager.try_get_working_organization_id()

    if download_data:
        data_provider_historical = "QuantConnect"

    paths_to_mount = None

    if data_provider_historical is not None:
        data_provider = non_interactive_config_build_for_name(lean_config, data_provider_historical,
                                                              cli_data_downloaders, kwargs, logger, environment_name)
        data_provider.ensure_module_installed(organization_id, container_module_version)
        container.lean_config_manager.set_properties(data_provider.get_settings())
        paths_to_mount = data_provider.get_paths_to_mount()

    lean_config_manager.configure_data_purchase_limit(lean_config, data_purchase_limit)

    if not output.exists():
        output.mkdir(parents=True)

    # This maybe overwritten by the addon module later if given.
    lean_config["messaging-handler"] = "QuantConnect.Messaging.Messaging"

    lean_runner = container.lean_runner

    # Set extra config
    for key, value in extra_config:
        if "environments" in lean_config and environment_name in lean_config["environments"] \
                and key in lean_config["environments"][environment_name]:
            lean_config["environments"][environment_name][key] = value
        else:
            lean_config[key] = value

    output_config_manager = container.output_config_manager
    lean_config["algorithm-id"] = str(output_config_manager.get_optimization_id(output))

    # Configure addon modules
    build_and_configure_modules(addon_module, cli_addon_modules, organization_id, lean_config,
                                kwargs, logger, environment_name, container_module_version)

    run_options = lean_runner.get_basic_docker_config(lean_config, algorithm_file, output, None, release, should_detach,
                                                      engine_image, paths_to_mount)

    run_options["working_dir"] = "/Lean/Optimizer.Launcher/bin/Debug"
    run_options["commands"].append(f"dotnet QuantConnect.Optimizer.Launcher.dll{' --estimate' if estimate else ''}")
    run_options["mounts"].append(
        Mount(target="/Lean/Optimizer.Launcher/bin/Debug/config.json",
              source=str(config_path),
              type="bind",
              read_only=True)
    )

    # Add known additional run options from the extra docker config
    LeanRunner.parse_extra_docker_config(run_options, loads(extra_docker_config))

    project_manager.copy_code(algorithm_file.parent, output / "code")

    success = container.docker_manager.run_image(engine_image, **run_options)

    cli_root_dir = container.lean_config_manager.get_cli_root_directory()
    relative_project_dir = project.relative_to(cli_root_dir)
    relative_output_dir = output.relative_to(cli_root_dir)

    if should_detach:
        temp_manager = container.temp_manager
        temp_manager.delete_temporary_directories_when_done = False

        logger.info(
            f"Successfully started optimization for '{relative_project_dir}' in the '{run_options['name']}' container")
        logger.info(f"The output will be stored in '{relative_output_dir}'")
        logger.info("You can use Docker's own commands to manage the detached container")
    elif success:
        optimizer_logs = (output / "log.txt").read_text(encoding="utf-8")

        if estimate:
            match = search(r"Optimization estimate: (\d+)", optimizer_logs)

            if match is None:
                raise RuntimeError(f"Something went wrong while running the optimization estimate, "
                                   f"the output is stored in '{relative_output_dir}'")

            backtestsCount = int(match[1])
            logger.info(f"Optimization estimate: \n"
                        f"  Total backtests: {backtestsCount}\n"
                        f"  Estimated runtime: {backtestsCount * latest_backtest_runtime / max_concurrent_backtests}")
        else:
            groups = findall(r"ParameterSet: \(([^)]+)\) backtestId '([^']+)'", optimizer_logs)

            if len(groups) > 0:
                optimal_parameters, optimal_id = groups[0]

                optimal_results = loads((output / optimal_id / f"{optimal_id}.json").read_text(encoding="utf-8"))
                optimal_backtest = QCBacktest(backtestId=optimal_id,
                                              projectId=1,
                                              status="",
                                              name=optimal_id,
                                              created=datetime.now(),
                                              completed=True,
                                              progress=1.0,
                                              runtimeStatistics=optimal_results["runtimeStatistics"],
                                              statistics=optimal_results["statistics"])

                logger.info(f"Optimal parameters: {optimal_parameters.replace(':', ': ').replace(',', ', ')}")
                logger.info(f"Optimal backtest results:")
                logger.info(optimal_backtest.get_statistics_table())

            logger.info(
                f"Successfully optimized '{relative_project_dir}' and stored the output in '{relative_output_dir}'")
    else:
        raise RuntimeError(
            f"Something went wrong while running the optimization, the output is stored in '{relative_output_dir}'")
