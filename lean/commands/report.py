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
from typing import Any, Dict, Optional

from click import command, option

from lean.click import LeanCommand, PathParameter
from lean.constants import DEFAULT_ENGINE_IMAGE, PROJECT_CONFIG_FILE_NAME
from lean.container import container
from lean.models.errors import MoreInfoError
from lean.components.util.live_utils import get_latest_result_json_file


def _find_project_directory(backtest_file: Path) -> Optional[Path]:
    """Returns the project directory, or None if backtest_file is not stored in a project directory.

    :param backtest_file: the path to the JSON file containing the backtest results
    :return: the path to the project directory, or None if backtest_file is stored outside a project directory
    """
    current_directory = backtest_file.parent

    # Loop until we find the root directory
    while current_directory != current_directory.parent:
        if (current_directory / PROJECT_CONFIG_FILE_NAME).is_file():
            return current_directory

        current_directory = current_directory.parent

    return None


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@option("--backtest-results",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              help="Path to the JSON file containing the backtest results")
@option("--live-results",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              help="Path to the JSON file containing the live trading results")
@option("--report-destination",
              type=PathParameter(exists=False, file_okay=True, dir_okay=False),
              default=lambda: Path.cwd() / "report.html",
              help="Path where the generated report is stored as HTML (defaults to ./report.html)")
@option("--detach", "-d",
              is_flag=True,
              default=False,
              help="Run the report creator in a detached Docker container and return immediately")
@option("--strategy-name",
              type=str,
              help="Name of the strategy, will appear at the top-right corner of each page")
@option("--strategy-version",
              type=str,
              help="Version number of the strategy, will appear next to the project name")
@option("--strategy-description",
              type=str,
              help="Description of the strategy, will appear under the 'Strategy Description' section")
@option("--overwrite",
              is_flag=True,
              default=False,
              help="Overwrite --report-destination if it already contains a file")
@option("--image",
              type=str,
              help=f"The LEAN engine image to use (defaults to {DEFAULT_ENGINE_IMAGE})")
@option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN engine image before running the report creator")
def report(backtest_results: Optional[Path],
           live_results: Optional[Path],
           report_destination: Path,
           detach: bool,
           strategy_name: Optional[str],
           strategy_version: Optional[str],
           strategy_description: Optional[str],
           overwrite: bool,
           image: Optional[str],
           update: bool) -> None:
    """Generate a report of a backtest.

    This runs the LEAN Report Creator in Docker to generate a polished, professional-grade report of a backtest.

    If --backtest-results is not given, a report is generated for the most recent local backtest.

    The name, description, and version are optional and will be blank if not given.

    If the given backtest data source file is stored in a project directory (or one of its subdirectories, like the
    default <project>/backtests/<timestamp>), the default name is the name of the project directory and the default
    description is the description stored in the project's config.json file.

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    from json import dump
    from docker.types import Mount

    if report_destination.exists() and not overwrite:
        raise RuntimeError(f"{report_destination} already exists, use --overwrite to overwrite it")

    environment = "backtests"
    output_config_manager = container.output_config_manager
    output_directory = output_config_manager.get_latest_output_directory(environment)

    if output_directory is None:
        raise ValueError(f"No output {environment} directories were found. "
                         f"Make sure you run a backtest or live deployment first.")

    if backtest_results is None:
        backtest_results = get_latest_result_json_file(output_directory)
        if not backtest_results:
            raise MoreInfoError(
            "Could not find a recent backtest result file, please use the --backtest-results option",
            "https://www.lean.io/docs/v2/lean-cli/reports#02-Generate-Reports"
            )

    logger = container.logger

    if live_results is None:
        logger.info(f"Generating a report from '{backtest_results}'")
    else:
        logger.info(f"Generating a report from '{backtest_results}' and '{live_results}'")

    project_directory = _find_project_directory(backtest_results)

    if project_directory is not None:
        if strategy_name is None:
            strategy_name = project_directory.name

        if strategy_description is None:
            project_config_manager = container.project_config_manager
            project_config = project_config_manager.get_project_config(project_directory)
            strategy_description = project_config.get("description", "")

    # The configuration given to the report creator
    # See https://github.com/QuantConnect/Lean/blob/master/Report/config.example.json
    report_config = {
        "data-folder": "/Lean/Data",
        "strategy-name": strategy_name or "",
        "strategy-version": strategy_version or "",
        "strategy-description": strategy_description or "",
        "live-data-source-file": "live-data-source-file.json" if live_results is not None else "",
        "backtest-data-source-file": "backtest-data-source-file.json",
        "report-destination": "/tmp/report.html",

        "environment": "report",

        "log-handler": "QuantConnect.Logging.CompositeLogHandler",
        "messaging-handler": "QuantConnect.Messaging.Messaging",
        "job-queue-handler": "QuantConnect.Queues.JobQueue",
        "api-handler": "QuantConnect.Api.Api",
        "map-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
        "factor-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
        "data-provider": "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
        "alpha-handler": "QuantConnect.Lean.Engine.Alphas.DefaultAlphaHandler",
        "data-channel-provider": "DataChannelProvider",

        "environments": {
            "report": {
                "live-mode": False,

                "setup-handler": "QuantConnect.Lean.Engine.Setup.ConsoleSetupHandler",
                "result-handler": "QuantConnect.Lean.Engine.Results.BacktestingResultHandler",
                "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.FileSystemDataFeed",
                "real-time-handler": "QuantConnect.Lean.Engine.RealTime.BacktestingRealTimeHandler",
                "history-provider": "QuantConnect.Lean.Engine.HistoricalData.SubscriptionDataReaderHistoryProvider",
                "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BacktestingTransactionHandler"
            }
        }
    }

    config_path = container.temp_manager.create_temporary_directory() / "config.json"
    with config_path.open("w+", encoding="utf-8") as file:
        dump(report_config, file)

    backtest_id = container.output_config_manager.get_backtest_id(output_directory)

    lean_config_manager = container.lean_config_manager
    data_dir = lean_config_manager.get_data_directory()

    report_destination.parent.mkdir(parents=True, exist_ok=True)

    run_options: Dict[str, Any] = {
        "detach": detach,
        "name": f"lean_cli_report_{backtest_id}",
        "working_dir": "/Lean/Report/bin/Debug",
        "commands": ["dotnet QuantConnect.Report.dll", f'cp /tmp/report.html "/Output/{report_destination.name}"'],
        "mounts": [
            Mount(target="/Lean/Report/bin/Debug/config.json",
                  source=str(config_path),
                  type="bind",
                  read_only=True),
            Mount(target="/Lean/Report/bin/Debug/backtest-data-source-file.json",
                  source=str(backtest_results),
                  type="bind",
                  read_only=True)
        ],
        "volumes": {
            str(data_dir): {
                "bind": "/Lean/Data",
                "mode": "rw"
            },
            str(report_destination.parent): {
                "bind": "/Output",
                "mode": "rw"
            }
        }
    }

    if live_results is not None:
        run_options["mounts"].append(Mount(target="/Lean/Report/bin/Debug/live-data-source-file.json",
                                           source=str(live_results),
                                           type="bind",
                                           read_only=True))

    cli_config_manager = container.cli_config_manager
    engine_image_override = image

    if engine_image_override is None and project_directory is not None:
        project_config_manager = container.project_config_manager
        project_config = project_config_manager.get_project_config(project_directory)
        engine_image_override = project_config.get("engine-image", None)

    engine_image = cli_config_manager.get_engine_image(engine_image_override)

    container.update_manager.pull_docker_image_if_necessary(engine_image, update)

    success = container.docker_manager.run_image(engine_image, **run_options)
    if not success:
        raise RuntimeError(
            "Something went wrong while running the LEAN Report Creator, see the logs above for more information")

    if detach:
        temp_manager = container.temp_manager
        temp_manager.delete_temporary_directories_when_done = False

        logger.info(f"Successfully started the report creator in the '{run_options['name']}' container")
        logger.info(f"The report will be generated to '{report_destination}'")
        logger.info("You can use Docker's own commands to manage the detached container")
        return

    logger.info(f"Successfully generated report to '{report_destination}'")
