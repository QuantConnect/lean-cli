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
from lean.click import LeanCommand, PathParameter, ensure_options
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.brokerages.local import all_local_brokerages, local_brokerage_data_feeds, all_local_data_feeds
from lean.models.errors import MoreInfoError
from lean.models.lean_config_configurer import LeanConfigConfigurer
from lean.models.logger import Option
from lean.models.configuration import InternalInputUserInput
from lean.models.click_options import options_from_json
from lean.models.json_module import JsonModule, LiveInitialStateInput
from lean.commands.live.live import live
from lean.components.util.live_utils import _get_configs_for_options, get_last_portfolio_cash_holdings, configure_initial_cash_balance, configure_initial_holdings,\
                                            _configure_initial_cash_interactively, _configure_initial_holdings_interactively
from lean.models.data_providers import all_data_providers

_environment_skeleton = {
    "live-mode": True,
    "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
    "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
    "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
    "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler"
}


def _get_configurable_modules_from_environment(lean_config: Dict[str, Any], environment_name: str) -> Tuple[LeanConfigConfigurer, List[LeanConfigConfigurer]]:
    """Returns the configurable modules from the given environment.

    :param lean_config: the LEAN configuration that should be used
    :param environment_name: the name of the environment
    :return: the configurable modules from the given environment
    """
    environment = lean_config["environments"][environment_name]
    for key in ["live-mode-brokerage", "data-queue-handler"]:
        if key not in environment:
            raise MoreInfoError(f"The '{environment_name}' environment does not specify a {key}",
                                "https://www.lean.io/docs/v2/lean-cli/live-trading/algorithm-control")

    brokerage = environment["live-mode-brokerage"]
    data_queue_handlers = environment["data-queue-handler"]
    [brokerage_configurer] = [local_brokerage for local_brokerage in all_local_brokerages if local_brokerage.get_live_name(environment_name) == brokerage]
    data_feed_configurers = [local_data_feed for local_data_feed in all_local_data_feeds if local_data_feed.get_live_name(environment_name) in data_queue_handlers]
    return brokerage_configurer, data_feed_configurers


def _install_modules(modules: List[LeanConfigConfigurer], user_kwargs: Dict[str, Any]) -> None:
    """Raises an error if any of the given modules are not installed.

    :param modules: the modules to check
    """
    for module in modules:
        if not module._installs:
            continue
        organization_id = container.organization_manager.try_get_working_organization_id()
        module.ensure_module_installed(organization_id)


def _raise_for_missing_properties(lean_config: Dict[str, Any], environment_name: str, lean_config_path: Path) -> None:
    """Raises an error if any required properties are missing.

    :param lean_config: the LEAN configuration that should be used
    :param environment_name: the name of the environment
    :param lean_config_path: the path to the LEAN configuration file
    """
    brokerage_configurer, data_feed_configurers = _get_configurable_modules_from_environment(lean_config, environment_name)
    brokerage_properties = brokerage_configurer.get_required_properties()
    data_queue_handler_properties = []
    for data_feed_configurer in data_feed_configurers:
        data_queue_handler_properties.extend(data_feed_configurer.get_required_properties())
    required_properties = list(set(brokerage_properties + data_queue_handler_properties))
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
https://www.lean.io/docs/v2/lean-cli/live-trading/brokerages/quantconnect-paper-trading
    """.strip())


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


def _configure_lean_config_interactively(lean_config: Dict[str, Any],
                                         environment_name: str,
                                         properties: Dict[str, Any],
                                         show_secrets: bool) -> None:
    """Interactively configures the Lean config to use.

    Asks the user all questions required to set up the Lean config for local live trading.

    :param lean_config: the base lean config to use
    :param environment_name: the name of the environment to configure
    :param properties: the properties to use to configure lean
    :param show_secrets: whether to show secrets on input
    """
    logger = container.logger

    lean_config["environments"] = {
        environment_name: _environment_skeleton
    }

    brokerage = logger.prompt_list("Select a brokerage", [
        Option(id=brokerage, label=brokerage.get_name()) for brokerage in all_local_brokerages
    ])

    brokerage.build(lean_config, logger, properties, hide_input=not show_secrets).configure(lean_config, environment_name)

    data_feeds = logger.prompt_list("Select a data feed", [
        Option(id=data_feed, label=data_feed.get_name()) for data_feed in local_brokerage_data_feeds[brokerage]
    ], multiple= True)
    for data_feed in data_feeds:
        if brokerage._id == data_feed._id:
            # update essential properties, so that other dependent values can be fetched.
            essential_properties_value = {brokerage.convert_lean_key_to_variable(config._id): config._value
                                          for config in brokerage.get_essential_configs()}
            properties.update(essential_properties_value)
            logger.debug(f"live.deploy._configure_lean_config_interactively(): essential_properties_value: {brokerage._id} {essential_properties_value}")
            # now required properties can be fetched as per data/filter provider from essential properties
            required_properties_value = {brokerage.convert_lean_key_to_variable(config._id): config._value
                                         for config in brokerage.get_required_configs([InternalInputUserInput])}
            properties.update(required_properties_value)
            logger.debug(f"live.deploy._configure_lean_config_interactively(): required_properties_value: {required_properties_value}")
        data_feed.build(lean_config, logger, properties, hide_input=not show_secrets).configure(lean_config, environment_name)


def _get_and_build_module(target_module_name: str, module_list: List[JsonModule], properties: Dict[str, Any]):
    logger = container.logger
    [target_module] = [module for module in module_list if module.get_name() == target_module_name]
    # update essential properties from brokerage to datafeed
    # needs to be updated before fetching required properties
    essential_properties = [target_module.convert_lean_key_to_variable(prop) for prop in target_module.get_essential_properties()]
    ensure_options(essential_properties)
    essential_properties_value = {target_module.convert_variable_to_lean_key(prop) : properties[prop] for prop in essential_properties}
    target_module.update_configs(essential_properties_value)
    logger.debug(f"live.deploy._get_and_build_module(): non-interactive: essential_properties_value with module {target_module_name}: {essential_properties_value}")
    # now required properties can be fetched as per data/filter provider from essential properties
    required_properties: List[str] = []
    for config in target_module.get_required_configs([InternalInputUserInput]):
        required_properties.append(target_module.convert_lean_key_to_variable(config._id))
    ensure_options(required_properties)
    required_properties_value = {target_module.convert_variable_to_lean_key(prop) : properties[prop] for prop in required_properties}
    target_module.update_configs(required_properties_value)
    logger.debug(f"live.deploy._get_and_build_module(): non-interactive: required_properties_value with module {target_module_name}: {required_properties_value}")
    return target_module


_cached_lean_config = None


# being used by lean.models.click_options.get_the_correct_type_default_value()
def _get_default_value(key: str) -> Optional[Any]:
    """Returns the default value for an option based on the Lean config.

    :param key: the name of the property in the Lean config that supplies the default value of an option
    :return: the value of the property in the Lean config, or None if there is none
    """
    global _cached_lean_config
    if _cached_lean_config is None:
        _cached_lean_config = container.lean_config_manager.get_lean_config()

    if key not in _cached_lean_config:
        return None

    value = _cached_lean_config[key]
    if value == "":
        return None

    return value


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
              type=Choice([b.get_name() for b in all_local_brokerages], case_sensitive=False),
              help="The brokerage to use")
@option("--data-feed",
              type=Choice([d.get_name() for d in all_local_data_feeds], case_sensitive=False),
              multiple=True,
              help="The data feed to use")
@option("--data-provider",
              type=Choice([dp.get_name() for dp in all_data_providers], case_sensitive=False),
              help="Update the Lean configuration file to retrieve data from the given provider")
@options_from_json(_get_configs_for_options("local"))
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
def deploy(project: Path,
           environment: Optional[str],
           output: Optional[Path],
           detach: bool,
           brokerage: Optional[str],
           data_feed: Optional[str],
           data_provider: Optional[str],
           release: bool,
           image: Optional[str],
           python_venv: Optional[str],
           live_cash_balance: Optional[str],
           live_holdings: Optional[str],
           update: bool,
           show_secrets: bool,
           **kwargs) -> None:
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
    from copy import copy
    from datetime import datetime
    # Reset globals so we reload everything in between tests
    global _cached_lean_config
    _cached_lean_config = None

    logger = container.logger

    project_manager = container.project_manager
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "live" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_config_manager = container.lean_config_manager

    if environment is not None and (brokerage is not None or len(data_feed) > 0):
        raise RuntimeError("--environment and --brokerage + --data-feed are mutually exclusive")

    if environment is not None:
        environment_name = environment
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)
    elif brokerage is not None or len(data_feed) > 0:
        ensure_options(["brokerage", "data_feed"])

        environment_name = "lean-cli"
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)

        lean_config["environments"] = {
            environment_name: copy(_environment_skeleton)
        }

        [brokerage_configurer] = [_get_and_build_module(brokerage, all_local_brokerages, kwargs)]
        brokerage_configurer.configure(lean_config, environment_name)

        for df in data_feed:
            [data_feed_configurer] = [_get_and_build_module(df, all_local_data_feeds, kwargs)]
            data_feed_configurer.configure(lean_config, environment_name)

    else:
        environment_name = "lean-cli"
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)
        _configure_lean_config_interactively(lean_config, environment_name, kwargs, show_secrets=show_secrets)

    if data_provider is not None:
        [data_provider_configurer] = [_get_and_build_module(data_provider, all_data_providers, kwargs)]
        data_provider_configurer.configure(lean_config, environment_name)

    if "environments" not in lean_config or environment_name not in lean_config["environments"]:
        lean_config_path = lean_config_manager.get_lean_config_path()
        raise MoreInfoError(f"{lean_config_path} does not contain an environment named '{environment_name}'",
                            "https://www.lean.io/docs/v2/lean-cli/live-trading/brokerages/quantconnect-paper-trading")

    if not lean_config["environments"][environment_name]["live-mode"]:
        raise MoreInfoError(f"The '{environment_name}' is not a live trading environment (live-mode is set to false)",
                            "https://www.lean.io/docs/v2/lean-cli/live-trading/brokerages/quantconnect-paper-trading")

    env_brokerage, env_data_queue_handlers = _get_configurable_modules_from_environment(lean_config, environment_name)
    _install_modules([env_brokerage] + env_data_queue_handlers, kwargs)

    _raise_for_missing_properties(lean_config, environment_name, lean_config_manager.get_lean_config_path())

    project_config_manager = container.project_config_manager
    cli_config_manager = container.cli_config_manager

    project_config = project_config_manager.get_project_config(algorithm_file.parent)
    engine_image = cli_config_manager.get_engine_image(image or project_config.get("engine-image", None))

    container.update_manager.pull_docker_image_if_necessary(engine_image, update)

    _start_iqconnect_if_necessary(lean_config, environment_name)

    if not output.exists():
        output.mkdir(parents=True)

    output_config_manager = container.output_config_manager
    lean_config["algorithm-id"] = f"L-{output_config_manager.get_live_deployment_id(output)}"

    if python_venv is not None and python_venv != "":
        lean_config["python-venv"] = f'{"/" if python_venv[0] != "/" else ""}{python_venv}'

    cash_balance_option, holdings_option, last_cash, last_holdings = get_last_portfolio_cash_holdings(container.api_client, env_brokerage,
                                                                                                      project_config.get("cloud-id", None), project)

    if environment is None and brokerage is None and len(data_feed) == 0:   # condition for using interactive panel
        if cash_balance_option != LiveInitialStateInput.NotSupported:
            live_cash_balance = _configure_initial_cash_interactively(logger, cash_balance_option, last_cash)

        if holdings_option != LiveInitialStateInput.NotSupported:
            live_holdings = _configure_initial_holdings_interactively(logger, holdings_option, last_holdings)
    else:
        if cash_balance_option != LiveInitialStateInput.NotSupported:
            live_cash_balance = configure_initial_cash_balance(logger, cash_balance_option, live_cash_balance, last_cash)
        elif live_cash_balance is not None and live_cash_balance != "":
            raise RuntimeError(f"Custom cash balance setting is not available for {brokerage}")

        if holdings_option != LiveInitialStateInput.NotSupported:
            live_holdings = configure_initial_holdings(logger, holdings_option, live_holdings, last_holdings)
        elif live_holdings is not None and live_holdings != "":
            raise RuntimeError(f"Custom portfolio holdings setting is not available for {brokerage}")

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

    if str(engine_image) != DEFAULT_ENGINE_IMAGE:
        logger.warn(f'A custom engine image: "{engine_image}" is being used!')

    lean_runner = container.lean_runner
    lean_runner.run_lean(lean_config, environment_name, algorithm_file, output, engine_image, None, release, detach)
