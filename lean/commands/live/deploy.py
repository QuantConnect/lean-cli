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
from typing import Any, Dict, List, Optional, Tuple
from click import option, argument, Choice
from lean.click import LeanCommand, PathParameter
from lean.components.util.name_rename import rename_internal_config_to_user_friendly_format
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.cli import (cli_brokerages, cli_data_queue_handlers, cli_data_downloaders,
                             cli_addon_modules, cli_history_provider)
from lean.models.errors import MoreInfoError
from lean.models.click_options import options_from_json, get_configs_for_options
from lean.models.json_module import LiveInitialStateInput, JsonModule
from lean.commands.live.live import live
from lean.components.util.live_utils import get_last_portfolio_cash_holdings, configure_initial_cash_balance, configure_initial_holdings,\
                                            _configure_initial_cash_interactively, _configure_initial_holdings_interactively
from lean.components.util.json_modules_handler import build_and_configure_modules, \
    non_interactive_config_build_for_name, interactive_config_build, config_build_for_name

_environment_skeleton = {
    "live-mode": True,
    "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
    "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
    "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
    "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
    "history-provider": ["SubscriptionDataReaderHistoryProvider"],
    "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"
}


def _start_iqconnect_if_necessary(lean_config: Dict[str, Any], environment_name: str) -> None:
    """Starts IQConnect if the given environment uses IQFeed as data queue handler.

    :param lean_config: the LEAN configuration that should be used
    :param environment_name: the name of the environment
    """
    from subprocess import Popen

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

    Popen(args)

    container.logger.info("Waiting 10 seconds for IQFeed to start")
    from time import sleep
    sleep(10)


def _get_history_provider_name(data_provider_live_names: [str]) -> [str]:
    """ Get name for history providers based on the live data providers

    :param data_provider_live_names: the current data provider live names
    """
    history_providers = []
    for potential_history_provider in cli_history_provider:
        if potential_history_provider.get_name() in data_provider_live_names:
            history_providers.append(potential_history_provider.get_name())
    return history_providers


@live.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True, default_command=True, name="deploy")
@argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@option("--environment",
              type=str,
              help="The environment to use")
@option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/live/TIMESTAMP)")
@option("--detach", "-d",
              is_flag=True,
              default=False,
              help="Run the live deployment in a detached Docker container and return immediately")
@option("--brokerage",
              type=Choice([b.get_name() for b in cli_brokerages], case_sensitive=False),
              help="The brokerage to use")
@option("--data-provider-live",
              type=Choice([d.get_name() for d in cli_data_queue_handlers], case_sensitive=False),
              multiple=True,
              help="The live data provider to use")
@option("--data-provider-historical",
              type=Choice([dp.get_name() for dp in cli_data_downloaders if dp.get_id() != "TerminalLinkBrokerage"], case_sensitive=False),
              help="Update the Lean configuration file to retrieve data from the given historical provider")
@options_from_json(get_configs_for_options("live-cli"))
@option("--release",
              is_flag=True,
              default=False,
              help="Compile C# projects in release configuration instead of debug")
@option("--image",
              type=str,
              help=f"The LEAN engine image to use (defaults to {DEFAULT_ENGINE_IMAGE})")
@option("--python-venv",
              type=str,
              help=f"The path of the python virtual environment to be used")
@option("--live-cash-balance",
              type=str,
              default="",
              help=f"A comma-separated list of currency:amount pairs of initial cash balance")
@option("--live-holdings",
              type=str,
              default="",
              help=f"A comma-separated list of symbol:symbolId:quantity:averagePrice of initial portfolio holdings")
@option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN engine image before starting live trading")
@option("--show-secrets", is_flag=True, show_default=True, default=False, help="Show secrets as they are input")
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
def deploy(project: Path,
           environment: Optional[str],
           output: Optional[Path],
           detach: bool,
           brokerage: Optional[str],
           data_provider_live: Optional[str],
           data_provider_historical: Optional[str],
           release: bool,
           image: Optional[str],
           python_venv: Optional[str],
           live_cash_balance: Optional[str],
           live_holdings: Optional[str],
           update: bool,
           show_secrets: bool,
           addon_module: Optional[List[str]],
           extra_config: Optional[Tuple[str, str]],
           extra_docker_config: Optional[str],
           no_update: bool,
           **kwargs) -> None:
    """Start live trading a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    By default an interactive wizard is shown letting you configure the brokerage and live data provider to use.
    If --environment, --brokerage or --data-provider-live are given the command runs in non-interactive mode.
    In this mode the CLI does not prompt for input.

    If --environment is given it must be the name of a live environment in the Lean configuration.

    If --brokerage and --data-provider-live are given, the options specific to the given brokerage/live data provider must also be given.
    The Lean config is used as fallback when a brokerage/live data provider-specific option hasn't been passed in.
    If a required option is not given and cannot be found in the Lean config the command aborts.

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    from copy import copy
    from datetime import datetime
    from json import loads

    logger = container.logger

    project_manager = container.project_manager
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "live" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_config_manager = container.lean_config_manager

    brokerage_instance: JsonModule
    data_provider_live_instances: [JsonModule] = []
    history_providers: [str] = []
    history_providers_instances: [JsonModule] = []
    data_downloader_instances: JsonModule
    if environment is not None and (brokerage is not None or len(data_provider_live) > 0):
        raise RuntimeError("--environment and --brokerage + --data-provider-live are mutually exclusive")

    environment_name = "lean-cli"
    if environment is not None:
        environment_name = environment
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)

        if environment_name in lean_config["environments"]:
            lean_environment = lean_config["environments"][environment_name]
            for key in ["live-mode-brokerage", "data-queue-handler", "history-provider"]:
                if key not in lean_environment:
                    raise MoreInfoError(f"The '{environment_name}' environment does not specify a {rename_internal_config_to_user_friendly_format(key)}",
                                        "https://www.lean.io/docs/v2/lean-cli/live-trading/algorithm-control")

            brokerage = lean_environment["live-mode-brokerage"]
            data_provider_live = lean_environment["data-queue-handler"]
            if type(data_provider_live) is not list:
                data_provider_live = [data_provider_live]
            history_providers = lean_environment["history-provider"]
            if type(history_providers) is not list:
                history_providers = [history_providers]
            logger.debug(f'Deploy(): loading env \'{environment_name}\'. Brokerage: \'{brokerage}\'. IDQHs: '
                         f'{data_provider_live}. HistoryProviders: {history_providers}')
        else:
            logger.info(f'Environment \'{environment_name}\' not found, creating from scratch')
            lean_config["environments"] = {environment_name: copy(_environment_skeleton)}
    else:
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)
        lean_config["environments"] = {environment_name: copy(_environment_skeleton)}

    if brokerage:
        # user provided brokerage, check all arguments were provided
        brokerage_instance = non_interactive_config_build_for_name(lean_config, brokerage, cli_brokerages, kwargs,
                                                                   logger, environment_name)
    else:
        # let the user choose the brokerage
        brokerage_instance = interactive_config_build(lean_config, cli_brokerages, logger, kwargs, show_secrets,
                                                      "Select a brokerage", multiple=False,
                                                      environment_name=environment_name)

    if data_provider_live and len(data_provider_live) > 0:
        for data_feed_name in data_provider_live:
            data_feed = non_interactive_config_build_for_name(lean_config, data_feed_name, cli_data_queue_handlers,
                                                              kwargs, logger, environment_name)
            data_provider_live_instances.append(data_feed)
    else:
        data_provider_live_instances = interactive_config_build(lean_config, cli_data_queue_handlers, logger, kwargs,
                                                                show_secrets, "Select a live data feed", multiple=True,
                                                                environment_name=environment_name)

    # based on the live data providers we set up the history providers
    data_provider_live = [provider.get_name() for provider in data_provider_live_instances]
    if data_provider_historical is None:
        data_provider_historical = "Local"
    data_downloader_instances = non_interactive_config_build_for_name(lean_config, data_provider_historical,
                                                                      cli_data_downloaders, kwargs, logger,
                                                                      environment_name)
    if history_providers is None or len(history_providers) == 0:
        history_providers = _get_history_provider_name(data_provider_live)
    for history_provider in history_providers:
        if history_provider in ["BrokerageHistoryProvider", "SubscriptionDataReaderHistoryProvider"]:
            continue
        history_providers_instances.append(config_build_for_name(lean_config, history_provider, cli_history_provider,
                                                                 kwargs, logger, interactive=True,
                                                                 environment_name=environment_name))

    engine_image, container_module_version, project_config = container.manage_docker_image(image, update, no_update,
                                                                                           algorithm_file.parent)

    organization_id = container.organization_manager.try_get_working_organization_id()
    paths_to_mount = {}
    for module in (data_provider_live_instances + [data_downloader_instances, brokerage_instance]
                   + history_providers_instances):
        module.ensure_module_installed(organization_id, container_module_version)
        paths_to_mount.update(module.get_paths_to_mount())

    if not lean_config["environments"][environment_name]["live-mode"]:
        raise MoreInfoError(f"The '{environment_name}' is not a live trading environment (live-mode is set to false)",
                            "https://www.lean.io/docs/v2/lean-cli/live-trading/brokerages/quantconnect-paper-trading")

    _start_iqconnect_if_necessary(lean_config, environment_name)

    if python_venv is not None and python_venv != "":
        lean_config["python-venv"] = f'{"/" if python_venv[0] != "/" else ""}{python_venv}'

    cash_balance_option, holdings_option, last_cash, last_holdings = get_last_portfolio_cash_holdings(
        container.api_client, brokerage_instance, project_config.get("cloud-id", None), project)

    # We cannot create the output directory before calling get_last_portfolio_holdings, since then the most recently
    # deployment would be always the local one (it has the current time in its name), and we would never be able to
    # use the cash and holdings from a cloud deployment (see live_utils._get_last_portfolio() method)
    if not output.exists():
        output.mkdir(parents=True)

    if environment is None and brokerage is None:   # condition for using interactive panel
        if cash_balance_option != LiveInitialStateInput.NotSupported:
            live_cash_balance = _configure_initial_cash_interactively(logger, cash_balance_option, last_cash)

        if holdings_option != LiveInitialStateInput.NotSupported:
            live_holdings = _configure_initial_holdings_interactively(logger, holdings_option, last_holdings)
    else:
        if cash_balance_option != LiveInitialStateInput.NotSupported:
            live_cash_balance = configure_initial_cash_balance(logger, cash_balance_option, live_cash_balance, last_cash)
        elif live_cash_balance is not None and live_cash_balance != "":
            raise RuntimeError(f"Custom cash balance setting is not available for {brokerage_instance}")

        if holdings_option != LiveInitialStateInput.NotSupported:
            live_holdings = configure_initial_holdings(logger, holdings_option, live_holdings, last_holdings)
        elif live_holdings is not None and live_holdings != "":
            raise RuntimeError(f"Custom portfolio holdings setting is not available for {brokerage_instance}")

    if live_cash_balance:
        lean_config["live-cash-balance"] = live_cash_balance
    if live_holdings:
        lean_config["live-holdings"] = [{
            "Symbol": {
                "Value": holding["symbol"],
                "ID": holding["symbolId"]
            },
            "Quantity": holding["quantity"],
            "AveragePrice": holding["averagePrice"]
        } for holding in live_holdings]

    # Set extra config
    given_algorithm_id = None
    for key, value in extra_config:
        if key == "algorithm-id":
            given_algorithm_id = int(value)
        else:
            lean_config[key] = value

    output_config_manager = container.output_config_manager
    lean_config["algorithm-id"] = f"L-{output_config_manager.get_live_deployment_id(output, given_algorithm_id)}"

    # Configure addon modules
    build_and_configure_modules(addon_module, cli_addon_modules, organization_id, lean_config,
                                kwargs, logger, environment_name, container_module_version)

    if container.platform_manager.is_host_arm():
        if "InteractiveBrokersBrokerage" in lean_config["environments"][environment_name]["live-mode-brokerage"] \
                or any("InteractiveBrokersBrokerage" in dataQueue for dataQueue in lean_config["environments"][environment_name]["data-queue-handler"]):
            raise RuntimeError(f"InteractiveBrokers is currently not supported for ARM hosts")

    lean_runner = container.lean_runner
    lean_runner.run_lean(lean_config,
                         environment_name,
                         algorithm_file,
                         output,
                         engine_image,
                         None,
                         release,
                         detach,
                         loads(extra_docker_config),
                         paths_to_mount)
