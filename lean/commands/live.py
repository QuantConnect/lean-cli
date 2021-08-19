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

from lean.click import LeanCommand, PathParameter, ensure_options
from lean.constants import DEFAULT_ENGINE_IMAGE, GUI_PRODUCT_ID
from lean.container import container
from lean.models.brokerages.local import all_local_brokerages, local_brokerage_data_feeds, all_local_data_feeds
from lean.models.brokerages.local.atreyu import AtreyuBrokerage
from lean.models.brokerages.local.binance import BinanceBrokerage, BinanceDataFeed
from lean.models.brokerages.local.bitfinex import BitfinexBrokerage, BitfinexDataFeed
from lean.models.brokerages.local.bloomberg import BloombergBrokerage, BloombergDataFeed
from lean.models.brokerages.local.coinbase_pro import CoinbaseProBrokerage, CoinbaseProDataFeed
from lean.models.brokerages.local.interactive_brokers import InteractiveBrokersBrokerage, InteractiveBrokersDataFeed
from lean.models.brokerages.local.iqfeed import IQFeedDataFeed
from lean.models.brokerages.local.oanda import OANDABrokerage, OANDADataFeed
from lean.models.brokerages.local.paper_trading import PaperTradingBrokerage
from lean.models.brokerages.local.tradier import TradierBrokerage, TradierDataFeed
from lean.models.brokerages.local.trading_technologies import TradingTechnologiesBrokerage, TradingTechnologiesDataFeed
from lean.models.brokerages.local.zerodha import ZerodhaBrokerage, ZerodhaDataFeed
from lean.models.errors import MoreInfoError
from lean.models.logger import Option

# Brokerage -> required configuration properties
_required_brokerage_properties = {
    "InteractiveBrokersBrokerage": ["ib-account", "ib-user-name", "ib-password",
                                    "ib-agent-description", "ib-trading-mode"],
    "TradierBrokerage": ["tradier-use-sandbox", "tradier-account-id", "tradier-access-token"],
    "OandaBrokerage": ["oanda-environment", "oanda-access-token", "oanda-account-id"],
    "GDAXBrokerage": ["gdax-api-secret", "gdax-api-key", "gdax-passphrase"],
    "BitfinexBrokerage": ["bitfinex-api-secret", "bitfinex-api-key"],
    "BinanceBrokerage": ["binance-api-secret", "binance-api-key"],
    "ZerodhaBrokerage": ["zerodha-access-token", "zerodha-api-key", "zerodha-product-type", "zerodha-trading-segment"],
    "BloombergBrokerage": ["job-organization-id", "bloomberg-api-type", "bloomberg-environment",
                           "bloomberg-server-host", "bloomberg-server-port", "bloomberg-emsx-broker"],
    "AtreyuBrokerage": ["job-organization-id", "atreyu-host", "atreyu-req-port", "atreyu-sub-port",
                        "atreyu-username", "atreyu-password",
                        "atreyu-client-id", "atreyu-broker-mpid", "atreyu-locate-rqd"],
    "TradingTechnologiesBrokerage": ["job-organization-id", "tt-user-name", "tt-session-password", "tt-account-name",
                                     "tt-rest-app-key", "tt-rest-app-secret", "tt-rest-environment",
                                     "tt-market-data-sender-comp-id", "tt-market-data-target-comp-id",
                                     "tt-market-data-host", "tt-market-data-port",
                                     "tt-order-routing-sender-comp-id", "tt-order-routing-target-comp-id",
                                     "tt-order-routing-host", "tt-order-routing-port",
                                     "tt-log-fix-messages"]
}

# Data queue handler -> required configuration properties
_required_data_queue_handler_properties = {
    "InteractiveBrokersBrokerage":
        _required_brokerage_properties["InteractiveBrokersBrokerage"] + ["ib-enable-delayed-streaming-data"],
    "TradierBrokerage": _required_brokerage_properties["TradierBrokerage"],
    "OandaBrokerage": _required_brokerage_properties["OandaBrokerage"],
    "GDAXDataQueueHandler": _required_brokerage_properties["GDAXBrokerage"],
    "BitfinexBrokerage": _required_brokerage_properties["BitfinexBrokerage"],
    "BinanceBrokerage": _required_brokerage_properties["BinanceBrokerage"],
    "ZerodhaBrokerage": _required_brokerage_properties["ZerodhaBrokerage"] + ["zerodha-history-subscription"],
    "BloombergBrokerage": _required_brokerage_properties["BloombergBrokerage"],
    "TradingTechnologiesBrokerage": _required_brokerage_properties["TradingTechnologiesBrokerage"],
    "QuantConnect.ToolBox.IQFeed.IQFeedDataQueueHandler": ["iqfeed-iqconnect", "iqfeed-productName", "iqfeed-version"]
}

_environment_skeleton = {
    "live-mode": True,
    "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
    "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
    "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
    "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler"
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
        environment_name: _environment_skeleton
    }

    brokerage = logger.prompt_list("Select a brokerage", [
        Option(id=brokerage, label=brokerage.get_name()) for brokerage in all_local_brokerages
    ])

    brokerage.build(lean_config, logger).configure(lean_config, environment_name)

    data_feed = logger.prompt_list("Select a data feed", [
        Option(id=data_feed, label=data_feed.get_name()) for data_feed in local_brokerage_data_feeds[brokerage]
    ])

    data_feed.build(lean_config, logger).configure(lean_config, environment_name)


_cached_organizations = None


def _get_organization_id(given_input: Optional[str], label: str) -> str:
    """Converts the organization name or id given by the user to an organization id.

    Shows an interactive wizard if no input is given.

    Raises an error if the user is not a member of an organization with the given name or id.

    :param given_input: the input given by the user
    :param label: the name of the module the organization id is needed for
    :return: the id of the organization given by the user
    """
    global _cached_organizations
    if _cached_organizations is None:
        api_client = container.api_client()
        _cached_organizations = api_client.organizations.get_all()

    if given_input is not None:
        organization = next((o for o in _cached_organizations if o.id == given_input or o.name == given_input), None)
        if organization is None:
            raise RuntimeError(f"You are not a member of an organization with name or id '{given_input}'")
    else:
        logger = container.logger()
        options = [Option(id=organization, label=organization.name) for organization in _cached_organizations]
        organization = logger.prompt_list(f"Select the organization with the {label} module subscription", options)

    return organization.id


_cached_lean_config = None


def _get_default_value(key: str) -> Optional[Any]:
    """Returns the default value for an option based on the Lean config.

    :param key: the name of the property in the Lean config that supplies the default value of an option
    :return: the value of the property in the Lean config, or None if there is none
    """
    global _cached_lean_config
    if _cached_lean_config is None:
        _cached_lean_config = container.lean_config_manager().get_lean_config()

    if key not in _cached_lean_config:
        return None

    value = _cached_lean_config[key]
    if value == "":
        return None

    if key == "iqfeed-iqconnect" and not Path(value).is_file():
        return None

    return value


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.option("--environment",
              type=str,
              help="The environment to use")
@click.option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/live/TIMESTAMP)")
@click.option("--detach", "-d",
              is_flag=True,
              default=False,
              help="Run the live deployment in a detached Docker container and return immediately")
@click.option("--gui",
              is_flag=True,
              default=False,
              help="Enable monitoring and controlling of the deployment via the local GUI")
@click.option("--gui-organization",
              type=str,
              default=lambda: _get_default_value("job-organization-id"),
              help="The name or id of the organization with the local GUI module subscription")
@click.option("--brokerage",
              type=click.Choice([b.get_name() for b in all_local_brokerages], case_sensitive=False),
              help="The brokerage to use")
@click.option("--data-feed",
              type=click.Choice([d.get_name() for d in all_local_data_feeds], case_sensitive=False),
              help="The data feed to use")
@click.option("--ib-user-name",
              type=str,
              default=lambda: _get_default_value("ib-user-name"),
              help="Your Interactive Brokers username")
@click.option("--ib-account",
              type=str,
              default=lambda: _get_default_value("ib-account"),
              help="Your Interactive Brokers account id")
@click.option("--ib-password",
              type=str,
              default=lambda: _get_default_value("ib-password"),
              help="Your Interactive Brokers password")
@click.option("--ib-enable-delayed-streaming-data",
              type=bool,
              default=lambda: _get_default_value("ib-enable-delayed-streaming-data"),
              help="Whether delayed data may be used when your algorithm subscribes to a security you don't have a market data subscription for")
@click.option("--tradier-account-id",
              type=str,
              default=lambda: _get_default_value("tradier-account-id"),
              help="Your Tradier account id")
@click.option("--tradier-access-token",
              type=str,
              default=lambda: _get_default_value("tradier-access-token"),
              help="Your Tradier access token")
@click.option("--tradier-use-sandbox",
              type=bool,
              default=lambda: _get_default_value("tradier-use-sandbox"),
              help="Whether the developer sandbox should be used")
@click.option("--oanda-account-id",
              type=str,
              default=lambda: _get_default_value("oanda-account-id"),
              help="Your OANDA account id")
@click.option("--oanda-access-token",
              type=str,
              default=lambda: _get_default_value("oanda-access-token"),
              help="Your OANDA API token")
@click.option("--oanda-environment",
              type=click.Choice(["Practice", "Trade"], case_sensitive=False),
              default=lambda: _get_default_value("oanda-environment"),
              help="The environment to run in, Practice for fxTrade Practice, Trade for fxTrade")
@click.option("--bitfinex-api-key",
              type=str,
              default=lambda: _get_default_value("bitfinex-api-key"),
              help="Your Bitfinex API key")
@click.option("--bitfinex-api-secret",
              type=str,
              default=lambda: _get_default_value("bitfinex-api-secret"),
              help="Your Bitfinex API secret")
@click.option("--gdax-api-key",
              type=str,
              default=lambda: _get_default_value("gdax-api-key"),
              help="Your Coinbase Pro API key")
@click.option("--gdax-api-secret",
              type=str,
              default=lambda: _get_default_value("gdax-api-secret"),
              help="Your Coinbase Pro API secret")
@click.option("--gdax-passphrase",
              type=str,
              default=lambda: _get_default_value("gdax-passphrase"),
              help="Your Coinbase Pro API passphrase")
@click.option("--gdax-use-sandbox",
              type=bool,
              default=lambda: _get_default_value("gdax-use-sandbox"),
              help="Whether the sandbox should be used")
@click.option("--binance-api-key",
              type=str,
              default=lambda: _get_default_value("binance-api-key"),
              help="Your Binance API key")
@click.option("--binance-api-secret",
              type=str,
              default=lambda: _get_default_value("binance-api-secret"),
              help="Your Binance API secret")
@click.option("--binance-use-testnet",
              type=bool,
              default=lambda: _get_default_value("binance-use-testnet"),
              help="Whether the testnet should be used")
@click.option("--zerodha-api-key",
              type=str,
              default=lambda: _get_default_value("zerodha-api-key"),
              help="Your Kite Connect API key")
@click.option("--zerodha-access-token",
              type=str,
              default=lambda: _get_default_value("zerodha-access-token"),
              help="Your Kite Connect access token")
@click.option("--zerodha-product-type",
              type=click.Choice(["MIS", "CNC", "NRML"], case_sensitive=False),
              default=lambda: _get_default_value("zerodha-product-type"),
              help="MIS if you are targeting intraday products, CNC if you are targeting delivery products, NRML if you are targeting carry forward products")
@click.option("--zerodha-trading-segment",
              type=click.Choice(["EQUITY", "COMMODITY"], case_sensitive=False),
              default=lambda: _get_default_value("zerodha-trading-segment"),
              help="EQUITY if you are trading equities on NSE or BSE, COMMODITY if you are trading commodities on MCX")
@click.option("--zerodha-history-subscription",
              type=bool,
              default=lambda: _get_default_value("zerodha-history-subscription"),
              help="Whether you have a history API subscription for Zerodha")
@click.option("--iqfeed-iqconnect",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              default=lambda: _get_default_value("iqfeed-iqconnect"),
              help="The path to the IQConnect binary")
@click.option("--iqfeed-username",
              type=str,
              default=lambda: _get_default_value("iqfeed-username"),
              help="Your IQFeed username")
@click.option("--iqfeed-password",
              type=str,
              default=lambda: _get_default_value("iqfeed-password"),
              help="Your IQFeed password")
@click.option("--iqfeed-product-name",
              type=str,
              default=lambda: _get_default_value("iqfeed-productName"),
              help="The product name of your IQFeed developer account")
@click.option("--iqfeed-version",
              type=str,
              default=lambda: _get_default_value("iqfeed-version"),
              help="The product version of your IQFeed developer account")
@click.option("--bloomberg-organization",
              type=str,
              default=lambda: _get_default_value("job-organization-id"),
              help="The name or id of the organization with the Bloomberg module subscription")
@click.option("--bloomberg-environment",
              type=click.Choice(["Production", "Beta"], case_sensitive=False),
              default=lambda: _get_default_value("bloomberg-environment"),
              help="The environment to run in")
@click.option("--bloomberg-server-host",
              type=str,
              default=lambda: _get_default_value("bloomberg-server-host"),
              help="The host of the Bloomberg server")
@click.option("--bloomberg-server-port",
              type=int,
              default=lambda: _get_default_value("bloomberg-server-port"),
              help="The port of the Bloomberg server")
@click.option("--bloomberg-symbol-map-file",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              default=lambda: _get_default_value("bloomberg-symbol-map-file"),
              help="The path to the Bloomberg symbol map file")
@click.option("--bloomberg-emsx-broker",
              type=str,
              default=lambda: _get_default_value("bloomberg-emsx-broker"),
              help="The EMSX broker to use")
@click.option("--bloomberg-emsx-user-time-zone",
              type=str,
              default=lambda: _get_default_value("bloomberg-emsx-user-time-zone"),
              help="The EMSX user timezone to use")
@click.option("--bloomberg-emsx-account",
              type=str,
              default=lambda: _get_default_value("bloomberg-emsx-account"),
              help="The EMSX account to use")
@click.option("--bloomberg-emsx-strategy",
              type=str,
              default=lambda: _get_default_value("bloomberg-emsx-strategy"),
              help="The EMSX strategy to use")
@click.option("--bloomberg-emsx-notes",
              type=str,
              default=lambda: _get_default_value("bloomberg-emsx-notes"),
              help="The EMSX notes to use")
@click.option("--bloomberg-emsx-handling",
              type=str,
              default=lambda: _get_default_value("bloomberg-emsx-handling"),
              help="The EMSX handling to use")
@click.option("--bloomberg-allow-modification",
              type=bool,
              default=lambda: _get_default_value("bloomberg-allow-modification"),
              help="Whether modification is allowed")
@click.option("--atreyu-organization",
              type=str,
              default=lambda: _get_default_value("job-organization-id"),
              help="The name or id of the organization with the Atreyu module subscription")
@click.option("--atreyu-host",
              type=str,
              default=lambda: _get_default_value("atreyu-host"),
              help="The host of the Atreyu server")
@click.option("--atreyu-req-port",
              type=int,
              default=lambda: _get_default_value("atreyu-req-port"),
              help="The Atreyu request port")
@click.option("--atreyu-sub-port",
              type=int,
              default=lambda: _get_default_value("atreyu-sub-port"),
              help="The Atreyu subscribe port")
@click.option("--atreyu-username",
              type=str,
              default=lambda: _get_default_value("atreyu-username"),
              help="Your Atreyu username")
@click.option("--atreyu-password",
              type=str,
              default=lambda: _get_default_value("atreyu-password"),
              help="Your Atreyu password")
@click.option("--atreyu-client-id",
              type=str,
              default=lambda: _get_default_value("atreyu-client-id"),
              help="Your Atreyu client id")
@click.option("--atreyu-broker-mpid",
              type=str,
              default=lambda: _get_default_value("atreyu-broker-mpid"),
              help="The broker MPID to use")
@click.option("--atreyu-locate-rqd",
              type=str,
              default=lambda: _get_default_value("atreyu-locate-rqd"),
              help="The locate rqd to use")
@click.option("--tt-organization",
              type=str,
              default=lambda: _get_default_value("job-organization-id"),
              help="The name or id of the organization with the Trading Technologies module subscription")
@click.option("--tt-user-name",
              type=str,
              default=lambda: _get_default_value("tt-user-name"),
              help="Your Trading Technologies username")
@click.option("--tt-session-password",
              type=str,
              default=lambda: _get_default_value("tt-session-password"),
              help="Your Trading Technologies session password")
@click.option("--tt-account-name",
              type=str,
              default=lambda: _get_default_value("tt-account-name"),
              help="Your Trading Technologies account name")
@click.option("--tt-rest-app-key",
              type=str,
              default=lambda: _get_default_value("tt-rest-app-key"),
              help="Your Trading Technologies REST app key")
@click.option("--tt-rest-app-secret",
              type=str,
              default=lambda: _get_default_value("tt-rest-app-secret"),
              help="Your Trading Technologies REST app secret")
@click.option("--tt-rest-environment",
              type=str,
              default=lambda: _get_default_value("tt-rest-environment"),
              help="The REST environment to run in")
@click.option("--tt-market-data-sender-comp-id",
              type=str,
              default=lambda: _get_default_value("tt-market-data-sender-comp-id"),
              help="The market data sender comp id to use")
@click.option("--tt-market-data-target-comp-id",
              type=str,
              default=lambda: _get_default_value("tt-market-data-target-comp-id"),
              help="The market data target comp id to use")
@click.option("--tt-market-data-host",
              type=str,
              default=lambda: _get_default_value("tt-market-data-host"),
              help="The host of the market data server")
@click.option("--tt-market-data-port",
              type=str,
              default=lambda: _get_default_value("tt-market-data-port"),
              help="The port of the market data server")
@click.option("--tt-order-routing-sender-comp-id",
              type=str,
              default=lambda: _get_default_value("tt-order-routing-sender-comp-id"),
              help="The order routing sender comp id to use")
@click.option("--tt-order-routing-target-comp-id",
              type=str,
              default=lambda: _get_default_value("tt-order-routing-target-comp-id"),
              help="The order routing target comp id to use")
@click.option("--tt-order-routing-host",
              type=str,
              default=lambda: _get_default_value("tt-order-routing-host"),
              help="The host of the order routing server")
@click.option("--tt-order-routing-port",
              type=str,
              default=lambda: _get_default_value("tt-order-routing-port"),
              help="The port of the order routing server")
@click.option("--tt-log-fix-messages",
              type=bool,
              default=lambda: _get_default_value("tt-log-fix-messages"),
              help="Whether FIX messages should be logged")
@click.option("--release",
              is_flag=True,
              default=False,
              help="Compile C# projects in release configuration instead of debug")
@click.option("--image",
              type=str,
              help=f"The LEAN engine image to use (defaults to {DEFAULT_ENGINE_IMAGE})")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN engine image before starting live trading")
def live(project: Path,
         environment: Optional[str],
         output: Optional[Path],
         detach: bool,
         gui: bool,
         gui_organization: Optional[str],
         brokerage: Optional[str],
         data_feed: Optional[str],
         ib_user_name: Optional[str],
         ib_account: Optional[str],
         ib_password: Optional[str],
         ib_enable_delayed_streaming_data: Optional[bool],
         tradier_account_id: Optional[str],
         tradier_access_token: Optional[str],
         tradier_use_sandbox: Optional[bool],
         oanda_account_id: Optional[str],
         oanda_access_token: Optional[str],
         oanda_environment: Optional[str],
         bitfinex_api_key: Optional[str],
         bitfinex_api_secret: Optional[str],
         gdax_api_key: Optional[str],
         gdax_api_secret: Optional[str],
         gdax_passphrase: Optional[str],
         gdax_use_sandbox: Optional[bool],
         binance_api_key: Optional[str],
         binance_api_secret: Optional[str],
         binance_use_testnet: Optional[bool],
         zerodha_api_key: Optional[str],
         zerodha_access_token: Optional[str],
         zerodha_product_type: Optional[str],
         zerodha_trading_segment: Optional[str],
         zerodha_history_subscription: Optional[bool],
         iqfeed_iqconnect: Optional[Path],
         iqfeed_username: Optional[str],
         iqfeed_password: Optional[str],
         iqfeed_product_name: Optional[str],
         iqfeed_version: Optional[str],
         bloomberg_organization: Optional[str],
         bloomberg_environment: Optional[str],
         bloomberg_server_host: Optional[str],
         bloomberg_server_port: Optional[int],
         bloomberg_symbol_map_file: Optional[Path],
         bloomberg_emsx_broker: Optional[str],
         bloomberg_emsx_user_time_zone: Optional[str],
         bloomberg_emsx_account: Optional[str],
         bloomberg_emsx_strategy: Optional[str],
         bloomberg_emsx_notes: Optional[str],
         bloomberg_emsx_handling: Optional[str],
         bloomberg_allow_modification: Optional[bool],
         atreyu_organization: Optional[str],
         atreyu_host: Optional[str],
         atreyu_req_port: Optional[int],
         atreyu_sub_port: Optional[int],
         atreyu_username: Optional[str],
         atreyu_password: Optional[str],
         atreyu_client_id: Optional[str],
         atreyu_broker_mpid: Optional[str],
         atreyu_locate_rqd: Optional[str],
         tt_organization: Optional[str],
         tt_user_name: Optional[str],
         tt_session_password: Optional[str],
         tt_account_name: Optional[str],
         tt_rest_app_key: Optional[str],
         tt_rest_app_secret: Optional[str],
         tt_rest_environment: Optional[str],
         tt_market_data_sender_comp_id: Optional[str],
         tt_market_data_target_comp_id: Optional[str],
         tt_market_data_host: Optional[str],
         tt_market_data_port: Optional[str],
         tt_order_routing_sender_comp_id: Optional[str],
         tt_order_routing_target_comp_id: Optional[str],
         tt_order_routing_host: Optional[str],
         tt_order_routing_port: Optional[str],
         tt_log_fix_messages: Optional[bool],
         release: bool,
         image: Optional[str],
         update: bool) -> None:
    """Start live trading a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    By default an interactive wizard is shown letting you configure the brokerage and data feed to use.
    If --environment, --brokerage or --data-feed are given the command runs in non-interactive mode.
    In this mode the CLI does not prompt for input.

    If --environment is given it must be the name of a live environment in the Lean configuration.

    If --brokerage and --data-feed are given, the options specific to the given brokerage/data feed must also be given.
    The Lean config is used as fallback when a brokerage/data feed-specific option hasn't been passed in.
    If a required option is not given and cannot be found in the Lean config the command aborts.

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    # Reset globals so we reload everything in between tests
    global _cached_organizations
    _cached_organizations = None
    global _cached_lean_config
    _cached_lean_config = None

    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "live" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if gui:
        module_manager = container.module_manager()
        module_manager.install_module(GUI_PRODUCT_ID, _get_organization_id(gui_organization, "local GUI"))

        detach = True

    lean_config_manager = container.lean_config_manager()

    if environment is not None and (brokerage is not None or data_feed is not None):
        raise RuntimeError("--environment and --brokerage + --data-feed are mutually exclusive")

    if environment is not None:
        environment_name = environment
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)
    elif brokerage is not None or data_feed is not None:
        ensure_options(["brokerage", "data_feed"])

        brokerage_configurer = None
        data_feed_configurer = None

        if brokerage == PaperTradingBrokerage.get_name():
            brokerage_configurer = PaperTradingBrokerage()
        elif brokerage == InteractiveBrokersBrokerage.get_name():
            ensure_options(["ib_user_name", "ib_account", "ib_password"])
            brokerage_configurer = InteractiveBrokersBrokerage(ib_user_name, ib_account, ib_password)
        elif brokerage == TradierBrokerage.get_name():
            ensure_options(["tradier_account_id", "tradier_access_token", "tradier_use_sandbox"])
            brokerage_configurer = TradierBrokerage(tradier_account_id, tradier_access_token, tradier_use_sandbox)
        elif brokerage == OANDABrokerage.get_name():
            ensure_options(["oanda_account_id", "oanda_access_token", "oanda_environment"])
            brokerage_configurer = OANDABrokerage(oanda_account_id, oanda_access_token, oanda_environment)
        elif brokerage == BitfinexBrokerage.get_name():
            ensure_options(["bitfinex_api_key", "bitfinex_api_secret"])
            brokerage_configurer = BitfinexBrokerage(bitfinex_api_key, bitfinex_api_secret)
        elif brokerage == CoinbaseProBrokerage.get_name():
            ensure_options(["gdax_api_key", "gdax_api_secret", "gdax_passphrase", "gdax_use_sandbox"])
            brokerage_configurer = CoinbaseProBrokerage(gdax_api_key,
                                                        gdax_api_secret,
                                                        gdax_passphrase,
                                                        gdax_use_sandbox)
        elif brokerage == BinanceBrokerage.get_name():
            ensure_options(["binance_api_key", "binance_api_secret", "binance_use_testnet"])
            brokerage_configurer = BinanceBrokerage(binance_api_key, binance_api_secret, binance_use_testnet)
        elif brokerage == ZerodhaBrokerage.get_name():
            ensure_options(["zerodha_api_key",
                            "zerodha_access_token",
                            "zerodha_product_type",
                            "zerodha_trading_segment"])
            brokerage_configurer = ZerodhaBrokerage(zerodha_api_key,
                                                    zerodha_access_token,
                                                    zerodha_product_type,
                                                    zerodha_trading_segment)
        elif brokerage == BloombergBrokerage.get_name():
            ensure_options(["bloomberg_environment",
                            "bloomberg_server_host",
                            "bloomberg_server_port",
                            "bloomberg_emsx_broker",
                            "bloomberg_allow_modification"])
            brokerage_configurer = BloombergBrokerage(_get_organization_id(bloomberg_organization, "Bloomberg"),
                                                      bloomberg_environment,
                                                      bloomberg_server_host,
                                                      bloomberg_server_port,
                                                      bloomberg_symbol_map_file,
                                                      bloomberg_emsx_broker,
                                                      bloomberg_emsx_user_time_zone,
                                                      bloomberg_emsx_account,
                                                      bloomberg_emsx_strategy,
                                                      bloomberg_emsx_notes,
                                                      bloomberg_emsx_handling,
                                                      bloomberg_allow_modification)
        elif brokerage == AtreyuBrokerage.get_name():
            ensure_options(["atreyu_host",
                            "atreyu_req_port",
                            "atreyu_sub_port",
                            "atreyu_username",
                            "atreyu_password",
                            "atreyu_client_id",
                            "atreyu_broker_mpid",
                            "atreyu_locate_rqd"])
            brokerage_configurer = AtreyuBrokerage(_get_organization_id(atreyu_organization, "Atreyu"),
                                                   atreyu_host,
                                                   atreyu_req_port,
                                                   atreyu_sub_port,
                                                   atreyu_username,
                                                   atreyu_password,
                                                   atreyu_client_id,
                                                   atreyu_broker_mpid,
                                                   atreyu_locate_rqd)
        elif brokerage == TradingTechnologiesBrokerage.get_name():
            ensure_options(["tt_user_name",
                            "tt_session_password",
                            "tt_account_name",
                            "tt_rest_app_key",
                            "tt_rest_app_secret",
                            "tt_rest_environment",
                            "tt_market_data_sender_comp_id",
                            "tt_market_data_target_comp_id",
                            "tt_market_data_host",
                            "tt_market_data_port",
                            "tt_order_routing_sender_comp_id",
                            "tt_order_routing_target_comp_id",
                            "tt_order_routing_host",
                            "tt_order_routing_port",
                            "tt_log_fix_messages"])
            brokerage_configurer = TradingTechnologiesBrokerage(_get_organization_id(tt_organization,
                                                                                     "Trading Technologies"),
                                                                tt_user_name,
                                                                tt_session_password,
                                                                tt_account_name,
                                                                tt_rest_app_key,
                                                                tt_rest_app_secret,
                                                                tt_rest_environment,
                                                                tt_market_data_sender_comp_id,
                                                                tt_market_data_target_comp_id,
                                                                tt_market_data_host,
                                                                tt_market_data_port,
                                                                tt_order_routing_sender_comp_id,
                                                                tt_order_routing_target_comp_id,
                                                                tt_order_routing_host,
                                                                tt_order_routing_port,
                                                                tt_log_fix_messages)

        if data_feed == InteractiveBrokersDataFeed.get_name():
            ensure_options(["ib_user_name", "ib_account", "ib_password", "ib_enable_delayed_streaming_data"])
            data_feed_configurer = InteractiveBrokersDataFeed(InteractiveBrokersBrokerage(ib_user_name,
                                                                                          ib_account,
                                                                                          ib_password),
                                                              ib_enable_delayed_streaming_data)
        elif data_feed == TradierDataFeed.get_name():
            ensure_options(["tradier_account_id", "tradier_access_token", "tradier_use_sandbox"])
            data_feed_configurer = TradierDataFeed(TradierBrokerage(tradier_account_id,
                                                                    tradier_access_token,
                                                                    tradier_use_sandbox))
        elif data_feed == OANDADataFeed.get_name():
            ensure_options(["oanda_account_id", "oanda_access_token", "oanda_environment"])
            data_feed_configurer = OANDADataFeed(OANDABrokerage(oanda_account_id,
                                                                oanda_access_token,
                                                                oanda_environment))
        elif data_feed == BitfinexDataFeed.get_name():
            ensure_options(["bitfinex_api_key", "bitfinex_api_secret"])
            data_feed_configurer = BitfinexDataFeed(BitfinexBrokerage(bitfinex_api_key, bitfinex_api_secret))
        elif data_feed == CoinbaseProDataFeed.get_name():
            ensure_options(["gdax_api_key", "gdax_api_secret", "gdax_passphrase", "gdax_use_sandbox"])
            data_feed_configurer = CoinbaseProDataFeed(CoinbaseProBrokerage(gdax_api_key,
                                                                            gdax_api_secret,
                                                                            gdax_passphrase,
                                                                            gdax_use_sandbox))
        elif data_feed == BinanceDataFeed.get_name():
            ensure_options(["binance_api_key", "binance_api_secret", "binance_use_testnet"])
            data_feed_configurer = BinanceDataFeed(BinanceBrokerage(binance_api_key,
                                                                    binance_api_secret,
                                                                    binance_use_testnet))
        elif data_feed == ZerodhaDataFeed.get_name():
            ensure_options(["zerodha_api_key",
                            "zerodha_access_token",
                            "zerodha_product_type",
                            "zerodha_trading_segment",
                            "zerodha_history_subscription"])
            data_feed_configurer = ZerodhaDataFeed(ZerodhaBrokerage(zerodha_api_key,
                                                                    zerodha_access_token,
                                                                    zerodha_product_type,
                                                                    zerodha_trading_segment),
                                                   zerodha_history_subscription)
        elif data_feed == BloombergDataFeed.get_name():
            ensure_options(["bloomberg_environment",
                            "bloomberg_server_host",
                            "bloomberg_server_port",
                            "bloomberg_emsx_broker",
                            "bloomberg_allow_modification"])
            data_feed_configurer = BloombergDataFeed(BloombergBrokerage(_get_organization_id(bloomberg_organization,
                                                                                             "Bloomberg"),
                                                                        bloomberg_environment,
                                                                        bloomberg_server_host,
                                                                        bloomberg_server_port,
                                                                        bloomberg_symbol_map_file,
                                                                        bloomberg_emsx_broker,
                                                                        bloomberg_emsx_user_time_zone,
                                                                        bloomberg_emsx_account,
                                                                        bloomberg_emsx_strategy,
                                                                        bloomberg_emsx_notes,
                                                                        bloomberg_emsx_handling,
                                                                        bloomberg_allow_modification))
        elif data_feed == TradingTechnologiesDataFeed.get_name():
            ensure_options(["tt_user_name",
                            "tt_session_password",
                            "tt_account_name",
                            "tt_rest_app_key",
                            "tt_rest_app_secret",
                            "tt_rest_environment",
                            "tt_market_data_sender_comp_id",
                            "tt_market_data_target_comp_id",
                            "tt_market_data_host",
                            "tt_market_data_port",
                            "tt_order_routing_sender_comp_id",
                            "tt_order_routing_target_comp_id",
                            "tt_order_routing_host",
                            "tt_order_routing_port",
                            "tt_log_fix_messages"])
            data_feed_configurer = TradingTechnologiesDataFeed(
                TradingTechnologiesBrokerage(_get_organization_id(tt_organization, "Trading Technologies"),
                                             tt_user_name,
                                             tt_session_password,
                                             tt_account_name,
                                             tt_rest_app_key,
                                             tt_rest_app_secret,
                                             tt_rest_environment,
                                             tt_market_data_sender_comp_id,
                                             tt_market_data_target_comp_id,
                                             tt_market_data_host,
                                             tt_market_data_port,
                                             tt_order_routing_sender_comp_id,
                                             tt_order_routing_target_comp_id,
                                             tt_order_routing_host,
                                             tt_order_routing_port,
                                             tt_log_fix_messages))
        elif data_feed == IQFeedDataFeed.get_name():
            ensure_options(["iqfeed_iqconnect",
                            "iqfeed_username",
                            "iqfeed_password",
                            "iqfeed_product_name",
                            "iqfeed_version"])
            data_feed_configurer = IQFeedDataFeed(iqfeed_iqconnect,
                                                  iqfeed_username,
                                                  iqfeed_password,
                                                  iqfeed_product_name,
                                                  iqfeed_version)

        environment_name = "lean-cli"
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)

        lean_config["environments"] = {
            environment_name: _environment_skeleton
        }

        brokerage_configurer.configure(lean_config, environment_name)
        data_feed_configurer.configure(lean_config, environment_name)
    else:
        environment_name = "lean-cli"
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)
        _configure_lean_config_interactively(lean_config, environment_name)

    if "environments" not in lean_config or environment_name not in lean_config["environments"]:
        lean_config_path = lean_config_manager.get_lean_config_path()
        raise MoreInfoError(f"{lean_config_path} does not contain an environment named '{environment_name}'",
                            "https://www.lean.io/docs/lean-cli/tutorials/live-trading/local-live-trading")

    if not lean_config["environments"][environment_name]["live-mode"]:
        raise MoreInfoError(f"The '{environment_name}' is not a live trading environment (live-mode is set to false)",
                            "https://www.lean.io/docs/lean-cli/tutorials/live-trading/local-live-trading")

    _raise_for_missing_properties(lean_config, environment_name, lean_config_manager.get_lean_config_path())

    project_config_manager = container.project_config_manager()
    cli_config_manager = container.cli_config_manager()

    project_config = project_config_manager.get_project_config(algorithm_file.parent)
    engine_image = cli_config_manager.get_engine_image(image or project_config.get("engine-image", None))

    container.update_manager().pull_docker_image_if_necessary(engine_image, update)

    _start_iqconnect_if_necessary(lean_config, environment_name)

    if not output.exists():
        output.mkdir(parents=True)

    output_config_manager = container.output_config_manager()
    lean_config["algorithm-id"] = f"L-{output_config_manager.get_live_deployment_id(output)}"

    if gui:
        lean_config["lean-manager-type"] = "QuantConnect.GUI.GuiLeanManager"
        output_config_manager.get_output_config(output).set("gui", True)

    lean_runner = container.lean_runner()
    lean_runner.run_lean(lean_config, environment_name, algorithm_file, output, engine_image, None, release, detach)

    if gui:
        logger = container.logger()
        logger.info(f"You can monitor the status of the live deployment in the GUI")
