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

from click import command, option, argument

from lean.click import LeanCommand, PathParameter
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@argument("backtest", type=str, required=False)
@option("--report-destination",
              type=PathParameter(exists=False, file_okay=True, dir_okay=False),
              default=lambda: Path.cwd() / "report.html",
              help="Path where the generated report is stored as HTML (defaults to ./report.html)")
@option("--css",
              type=PathParameter(exists=False, file_okay=True, dir_okay=False),
              help="Path where the CSS override file is stored")
@option("--html",
              type=PathParameter(exists=False, file_okay=True, dir_okay=False),
              help="Path where the custom HTML template file is stored")
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
@option("--pdf",
              is_flag=True,
              default=False,
              help="Create a PDF version along with the HTML version of the report")
def report(backtest: Optional[str],
           report_destination: Path,
           css: Optional[Path],
           html: Optional[Path],
           detach: bool,
           strategy_name: Optional[str],
           strategy_version: Optional[str],
           strategy_description: Optional[str],
           overwrite: bool,
           image: Optional[str],
           update: bool,
           pdf: bool) -> None:
    """Generate a report from a cloud backtest.

    This fetches the backtest results from the cloud and runs the LEAN Report Creator
    in Docker to generate a polished, professional-grade report.

    BACKTEST can be a backtest ID or name. If not specified, uses the most recent
    completed backtest.

    The name, description, and version are optional and will be blank if not given.

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    from json import dump
    from docker.types import Mount

    logger = container.logger
    data_server_client = container.data_server_client

    if data_server_client is None:
        raise RuntimeError("Cloud report requires Cascade data server. Configure with `lean login`.")

    if report_destination.exists() and not overwrite:
        raise RuntimeError(f"{report_destination} already exists, use --overwrite to overwrite it")

    # Find the backtest
    backtest_data = None
    if backtest is None:
        # Get the latest completed backtest
        logger.info("No backtest specified, using most recent completed backtest...")
        backtest_data = data_server_client.get_latest_backtest(status="completed")
        if backtest_data is None:
            raise RuntimeError("No completed backtests found. Run a backtest first with `lean cloud backtest`.")
    else:
        # Try to find by ID first, then by name
        try:
            backtest_data = data_server_client.get_backtest(backtest)
        except Exception:
            # Try by name
            backtest_data = data_server_client.get_backtest_by_name(backtest)
            if backtest_data is None:
                raise RuntimeError(f"No backtest found with ID or name '{backtest}'")

    backtest_id = backtest_data["id"]
    backtest_name = backtest_data.get("name", "unnamed")
    backtest_status = backtest_data.get("status", "unknown")

    if backtest_status != "completed":
        raise RuntimeError(f"Backtest '{backtest_name}' has status '{backtest_status}'. Only completed backtests can generate reports.")

    logger.info(f"Generating report for backtest '{backtest_name}' ({backtest_id})")

    # Fetch the backtest results
    logger.info("Fetching backtest results from cloud...")
    try:
        backtest_results = data_server_client.get_backtest_results(backtest_id)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch backtest results: {e}")

    # Save results to a temporary file
    temp_manager = container.temp_manager
    results_dir = temp_manager.create_temporary_directory()
    results_file = results_dir / "backtest-results.json"
    with results_file.open("w+", encoding="utf-8") as file:
        dump(backtest_results, file)

    logger.info(f"Generating report from cloud backtest results...")

    # Use backtest name as strategy name if not provided
    if strategy_name is None:
        strategy_name = backtest_name

    # The configuration given to the report creator
    # See https://github.com/QuantConnect/Lean/blob/master/Report/config.example.json
    report_config = {
        "data-folder": "/Lean/Data",
        "strategy-name": strategy_name or "",
        "strategy-version": strategy_version or "",
        "strategy-description": strategy_description or "",
        "live-data-source-file": "",
        "backtest-data-source-file": "backtest-data-source-file.json",
        "report-destination": "/tmp/report.html",
        "report-css-override-file": "report_override.css" if (css is not None) and (css.exists()) else "",
        "report-html-custom-file": "template_custom.html" if (html is not None) and (html.exists()) else "",
        "report-format": "pdf" if pdf else "",
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

    config_path = temp_manager.create_temporary_directory() / "config.json"
    with config_path.open("w+", encoding="utf-8") as file:
        dump(report_config, file)

    lean_config_manager = container.lean_config_manager
    data_dir = lean_config_manager.get_data_directory()

    report_destination.parent.mkdir(parents=True, exist_ok=True)

    run_options: Dict[str, Any] = {
        "detach": detach,
        "name": f"lean_cli_cloud_report_{backtest_id[:8]}",
        "working_dir": "/Lean/Report/bin/Debug",
        "commands": ["dotnet QuantConnect.Report.dll", f'cp /tmp/report.html "/Output/{report_destination.name}"'],
        "mounts": [
            Mount(target="/Lean/Report/bin/Debug/config.json",
                  source=str(config_path),
                  type="bind",
                  read_only=True),
            Mount(target="/Lean/Report/bin/Debug/backtest-data-source-file.json",
                  source=str(results_file),
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

    if css is not None:
        if css.exists():
            run_options["mounts"].append(Mount(target="/Lean/Report/bin/Debug/report_override.css",
                                               source=str(css),
                                               type="bind",
                                               read_only=True))
        else:
            logger.info(f"CSS override file '{css}' could not be found")

    if html is not None:
        if html.exists():
            run_options["mounts"].append(Mount(target="/Lean/Report/bin/Debug/template_custom.html",
                                               source=str(html),
                                               type="bind",
                                               read_only=True))
        else:
            logger.info(f"Custom HTML template file '{html}' could not be found")

    if pdf:
        run_options["commands"].append(f'cp /tmp/report.pdf "/Output/{report_destination.name.replace(".html", ".pdf")}"')

    engine_image, container_module_version, project_config = container.manage_docker_image(image, update, False, None)

    success = container.docker_manager.run_image(engine_image, **run_options)
    if not success:
        raise RuntimeError(
            "Something went wrong while running the LEAN Report Creator, see the logs above for more information")

    if detach:
        temp_manager.delete_temporary_directories_when_done = False

        logger.info(f"Successfully started the report creator in the '{run_options['name']}' container")
        logger.info(f"The report will be generated to '{report_destination}'")
        logger.info("You can use Docker's own commands to manage the detached container")
        return

    logger.info(f"Successfully generated report to '{report_destination}'")
