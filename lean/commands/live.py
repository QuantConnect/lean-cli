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

import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import click

from lean.click import LeanCommand, PathParameter
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.brokerages.local import all_local_brokerages, local_brokerage_data_feeds
from lean.models.brokerages.local.iqfeed import IQFeedDataFeed
from lean.models.errors import MoreInfoError
from lean.models.logger import Option

# Brokerage -> required configuration properties
_required_brokerage_properties = {
    "InteractiveBrokersBrokerage": ["ib-account", "ib-user-name", "ib-password",
                                    "ib-agent-description", "ib-trading-mode", "ib-enable-delayed-streaming-data"],
    "TradierBrokerage": ["tradier-use-sandbox", "tradier-account-id", "tradier-access-token"],
    "OandaBrokerage": ["oanda-environment", "oanda-access-token", "oanda-account-id"],
    "GDAXBrokerage": ["gdax-api-secret", "gdax-api-key", "gdax-passphrase"],
    "BitfinexBrokerage": ["bitfinex-api-secret", "bitfinex-api-key"],
    "BinanceBrokerage": ["binance-api-secret", "binance-api-key"],
    "ZerodhaBrokerage": ["zerodha-access-token", "zerodha-api-key",
                         "zerodha-product-type", "zerodha-trading-segment", "zerodha-history-subscription"]
}

# Data queue handler -> required configuration properties
_required_data_queue_handler_properties = {
    "QuantConnect.Brokerages.InteractiveBrokers.InteractiveBrokersBrokerage":
        _required_brokerage_properties["InteractiveBrokersBrokerage"],
    "TradierBrokerage": _required_brokerage_properties["TradierBrokerage"],
    "OandaBrokerage": _required_brokerage_properties["OandaBrokerage"],
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
                                "https://www.lean.io/docs/lean-cli/tutorials/live-trading/local-live-trading")

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
https://www.lean.io/docs/lean-cli/tutorials/live-trading/local-live-trading
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


def _configure_lean_config_interactively(lean_config: Dict[str, Any], environment_name: str) -> None:
    """Interactively configures the Lean config to use.

    Asks the user all questions required to set up the Lean config for local live trading.

    :param lean_config: the base lean config to use
    :param environment_name: the name of the environment to configure
    """
    logger = container.logger()

    lean_config["environments"] = {
        environment_name: {
            "live-mode": True,
            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler"
        }
    }

    brokerage = logger.prompt_list("Select a brokerage", [
        Option(id=brokerage, label=brokerage.get_name()) for brokerage in all_local_brokerages
    ])

    brokerage.configure(lean_config, environment_name, logger)

    data_feeds = local_brokerage_data_feeds[brokerage]
    if platform.system() == "Windows":
        data_feeds.append(IQFeedDataFeed)

    data_feed = logger.prompt_list("Select a data feed", [
        Option(id=data_feed, label=data_feed.get_name()) for data_feed in data_feeds
    ])

    data_feed.configure(lean_config, environment_name, logger)


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.option("--environment",
              type=str,
              help="The environment to use")
@click.option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/live/TIMESTAMP)")
@click.option("--image",
              type=str,
              help=f"The LEAN engine image to use (defaults to {DEFAULT_ENGINE_IMAGE})")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN engine image before starting live trading")
def live(project: Path, environment: Optional[str], output: Optional[Path], image: Optional[str], update: bool) -> None:
    """Start live trading a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    If --environment is given it must be the name of a live environment in the Lean configuration.
    If --environment is not given an interactive wizard will show letting you configure which brokerage to use.

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "live" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_config_manager = container.lean_config_manager()

    if environment is None:
        environment = "lean-cli"
        lean_config = lean_config_manager.get_complete_lean_config(environment, algorithm_file, None, None)
        _configure_lean_config_interactively(lean_config, environment)
    else:
        lean_config = lean_config_manager.get_complete_lean_config(environment, algorithm_file, None, None)

    if "environments" not in lean_config or environment not in lean_config["environments"]:
        lean_config_path = lean_config_manager.get_lean_config_path()
        raise MoreInfoError(f"{lean_config_path} does not contain an environment named '{environment}'",
                            "https://www.lean.io/docs/lean-cli/tutorials/live-trading/local-live-trading")

    if not lean_config["environments"][environment]["live-mode"]:
        raise MoreInfoError(f"The '{environment}' is not a live trading environment (live-mode is set to false)",
                            "https://www.lean.io/docs/lean-cli/tutorials/live-trading/local-live-trading")

    _raise_for_missing_properties(lean_config, environment, lean_config_manager.get_lean_config_path())
    _start_iqconnect_if_necessary(lean_config, environment)

    cli_config_manager = container.cli_config_manager()
    engine_image = cli_config_manager.get_engine_image(image)

    docker_manager = container.docker_manager()

    if update or not docker_manager.supports_dotnet_5(engine_image):
        docker_manager.pull_image(engine_image)

    lean_runner = container.lean_runner()
    lean_runner.run_lean(lean_config, environment, algorithm_file, output, engine_image, None)

    if str(engine_image) == DEFAULT_ENGINE_IMAGE and not update:
        update_manager = container.update_manager()
        update_manager.warn_if_docker_image_outdated(engine_image)
