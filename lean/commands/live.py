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

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import click

from lean.click import LeanCommand, PathParameter
from lean.constants import ENGINE_IMAGE
from lean.container import container
from lean.models.errors import MoreInfoError

# Brokerage -> required configuration properties
_required_brokerage_properties = {
    "InteractiveBrokersBrokerage": ["ib-account", "ib-user-name", "ib-password",
                                    "ib-agent-description", "ib-trading-mode", "ib-enable-delayed-streaming-data"],
    "TradierBrokerage": ["tradier-use-sandbox", "tradier-account-id", "tradier-access-token"],
    "OandaBrokerage": ["oanda-environment", "oanda-access-token", "oanda-account-id"],
    "FxcmBrokerage": ["fxcm-server", "fxcm-terminal", "fxcm-user-name", "fxcm-password", "fxcm-account-id"],
    "GDAXBrokerage": ["gdax-api-secret", "gdax-api-key", "gdax-passphrase"],
    "BitfinexBrokerage": ["bitfinex-api-secret", "bitfinex-api-key"],
    "BinanceBrokerage": ["binance-api-secret", "binance-api-key"],
    "ZerodhaBrokerage": ["zerodha-access-token", "zerodha-api-key",
                         "zerodha-product-type", "zeroda-trading-segment", "zerodha-history-subscription"]
}

# Data queue handler -> required configuration properties
_required_data_queue_handler_properties = {
    "QuantConnect.Brokerages.InteractiveBrokers.InteractiveBrokersBrokerage":
        _required_brokerage_properties["InteractiveBrokersBrokerage"],
    "TradierBrokerage": _required_brokerage_properties["TradierBrokerage"],
    "OandaBrokerage": _required_brokerage_properties["OandaBrokerage"],
    "FxcmBrokerage": _required_brokerage_properties["FxcmBrokerage"],
    "GDAXDataQueueHandler": _required_brokerage_properties["GDAXBrokerage"],
    "BitfinexBrokerage": _required_brokerage_properties["BitfinexBrokerage"],
    "BinanceBrokerage": _required_brokerage_properties["BinanceBrokerage"],
    "ZerodhaBrokerage": _required_brokerage_properties["ZerodhaBrokerage"],
    "QuantConnect.ToolBox.IQFeed.IQFeedDataQueueHandler": ["iqfeed-iqconnect", "iqfeed-productName", "iqfeed-version"]
}


def _raise_for_missing_properties(lean_config: Dict[str, Any], environment_name: str, lean_config_path: Path) -> None:
    """Raises an error if any required properties are missing.

    :param lean_config: the LEAN configuration that should be used
    :param environment_name: the name of the environment
    :param lean_config_path: the path to the LEAN configuration file
    """
    environment = lean_config["environments"][environment_name]
    for key in ["live-mode-brokerage", "data-queue-handler"]:
        if key not in environment:
            raise MoreInfoError(f"The '{environment_name}' environment does not specify a {key}",
                                "https://www.quantconnect.com/docs/v2/lean-cli/tutorials/live-trading/local-live-trading")

    brokerage = environment["live-mode-brokerage"]
    data_queue_handler = environment["data-queue-handler"]

    brokerage_properties = _required_brokerage_properties.get(brokerage, [])
    data_queue_handler_properties = _required_data_queue_handler_properties.get(data_queue_handler, [])

    required_properties = brokerage_properties + data_queue_handler_properties
    missing_properties = [p for p in required_properties if p not in lean_config or lean_config[p] == ""]
    missing_properties = set(missing_properties)
    if len(missing_properties) == 0:
        return

    properties_str = "properties" if len(missing_properties) > 1 else "property"
    these_str = "these" if len(missing_properties) > 1 else "this"

    missing_properties = "\n".join(f"- {p}" for p in missing_properties)

    raise RuntimeError(f"""
Please configure the following missing {properties_str} in {lean_config_path}:
{missing_properties}
Go to the following url for documentation on {these_str} {properties_str}:
https://www.quantconnect.com/docs/v2/lean-cli/tutorials/live-trading/local-live-trading
    """.strip())


def _start_iqconnect_if_necessary(lean_config: Dict[str, Any], environment_name: str) -> None:
    """Starts IQConnect if the given environment uses IQFeed as data queue handler.

    :param lean_config: the LEAN configuration that should be used
    :param environment_name: the name of the environment
    """
    environment = lean_config["environments"][environment_name]
    if environment["data-queue-handler"] != "QuantConnect.ToolBox.IQFeed.IQFeedDataQueueHandler":
        return

    args = [lean_config["iqfeed-iqconnect"],
            "-product", lean_config["iqfeed-productName"],
            "-version", lean_config["iqfeed-version"]]

    username = lean_config.get("iqfeed-username", "")
    if username != "":
        args.extend(["-login", username])

    password = lean_config.get("iqfeed-password", "")
    if password != "":
        args.extend(["-password", password])

    subprocess.Popen(args)

    container.logger().info("Waiting 10 seconds for IQFeed to start")
    time.sleep(10)


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.argument("environment", type=str)
@click.option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/live/TIMESTAMP)")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the selected LEAN engine version before starting live trading")
@click.option("--version",
              type=str,
              default="latest",
              help="The LEAN engine version to run (defaults to the latest installed version)")
def live(project: Path, environment: str, output: Optional[Path], update: bool, version: str) -> None:
    """Start live trading a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    ENVIRONMENT must be the name of an environment in the Lean configuration file with live-mode set to true.
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "live" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_config_manager = container.lean_config_manager()
    lean_config = lean_config_manager.get_complete_lean_config(environment, algorithm_file, None)

    if "environments" not in lean_config or environment not in lean_config["environments"]:
        lean_config_path = lean_config_manager.get_lean_config_path()
        raise MoreInfoError(f"{lean_config_path} does not contain an environment named '{environment}'",
                            "https://www.quantconnect.com/docs/v2/lean-cli/tutorials/live-trading/local-live-trading")

    if not lean_config["environments"][environment]["live-mode"]:
        raise MoreInfoError(f"The '{environment}' is not a live trading environment (live-mode is set to false)",
                            "https://www.quantconnect.com/docs/v2/lean-cli/tutorials/live-trading/local-live-trading")

    _raise_for_missing_properties(lean_config, environment, lean_config_manager.get_lean_config_path())
    _start_iqconnect_if_necessary(lean_config, environment)

    docker_manager = container.docker_manager()

    if version != "latest":
        if not docker_manager.tag_exists(ENGINE_IMAGE, version):
            raise RuntimeError(
                f"The specified version does not exist, please pick a valid tag from https://hub.docker.com/r/{ENGINE_IMAGE}/tags")

    if update:
        docker_manager.pull_image(ENGINE_IMAGE, version)

    lean_runner = container.lean_runner()
    lean_runner.run_lean(environment, algorithm_file, output, version, None)

    if version == "latest" and not update:
        update_manager = container.update_manager()
        update_manager.warn_if_docker_image_outdated(ENGINE_IMAGE)
