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

import copy
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import click
from lean.click import LeanCommand, PathParameter, ensure_options
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.brokerages.local import all_local_brokerages, local_brokerage_data_feeds, all_local_data_feeds
from lean.models.errors import MoreInfoError
from lean.models.logger import Option
from lean.models.configuration import Configuration, InfoConfiguration, InternalInputUserInput
from lean.models.click_options import options_from_json
from lean.models.json_module import JsonModule
from lean.commands.live.live import live
from lean.models.data_providers import all_data_providers

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
                                "https://www.lean.io/docs/lean-cli/live-trading")

    brokerage = environment["live-mode-brokerage"]
    data_queue_handlers = environment["data-queue-handler"]

    [brokerage_configurer] = [local_brokerage for local_brokerage in all_local_brokerages if local_brokerage.get_live_name(environment_name) == brokerage]
    data_feed_configurers = [local_data_feed for local_data_feed in all_local_data_feeds if local_data_feed.get_live_name(environment_name) in data_queue_handlers]
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
https://www.lean.io/docs/lean-cli/live-trading
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

    data_feeds = logger.prompt_list("Select a data feed", [
        Option(id=data_feed, label=data_feed.get_name()) for data_feed in local_brokerage_data_feeds[brokerage]
    ], multiple= True)
    for data_feed in data_feeds:
        if brokerage._id == data_feed._id:
            # update essential properties, so that other dependent values can be fetched.
            essential_properties_value = {config._id : config._value for config in brokerage.get_essential_configs()}
            data_feed.update_configs(essential_properties_value)
            # now required properties can be fetched as per data/filter provider from esssential properties
            required_properties_value = {config._id : config._value for config in brokerage.get_required_configs([InternalInputUserInput])}
            data_feed.update_configs(required_properties_value)
            # mark configs are updated
            #TODO: create a setter method to set the property instead.
            setattr(data_feed, '_is_installed_and_build', True)
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

def _get_and_build_module(target_module_name: str, module_list: List[JsonModule], properties: Dict[str, Any]):
    [target_module] = [module for module in module_list if module.get_name() == target_module_name]
    # update essential properties from brokerage to datafeed
    # needs to be updated before fetching required properties
    essential_properties = [target_module._convert_lean_key_to_variable(prop) for prop in target_module.get_essential_properties()]
    ensure_options(essential_properties)
    essential_properties_value = {target_module._convert_variable_to_lean_key(prop) : properties[prop] for prop in essential_properties}
    target_module.update_configs(essential_properties_value)
    # now required properties can be fetched as per data/filter provider from esssential properties
    required_properties: List[str] = []
    organization_info: Dict[str,str] = {}
    for config in target_module.get_required_configs([InternalInputUserInput]):
        if config.is_type_organization_id:
            organization_info[config._id] = _get_organization_id(properties[target_module._convert_lean_key_to_variable(config._id)], target_module._id)
            properties[target_module._convert_lean_key_to_variable(config._id)] = organization_info[config._id]
            # skip organization id from ensure_options() because it is fetched using _get_organization_id()
            continue
        required_properties.append(target_module._convert_lean_key_to_variable(config._id)) 
    ensure_options(required_properties)
    required_properties_value = {target_module._convert_variable_to_lean_key(prop) : properties[prop] for prop in required_properties}
    required_properties_value.update(organization_info)
    target_module.update_configs(required_properties_value)    
    return target_module

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

    return value

def _get_configs_for_options() -> List[Configuration]: 
    run_options: Dict[str, Configuration] = {}
    config_with_module_id: Dict[str, str] = {}
    for module in all_local_brokerages + all_local_data_feeds + all_data_providers:
        for config in module.get_all_input_configs([InternalInputUserInput, InfoConfiguration]):
            if config._id in run_options:
                if (config._id in config_with_module_id 
                    and config_with_module_id[config._id] == module._id):
                    # config of same module
                    continue
                else:
                    raise ValueError(f'Options names should be unique. Duplicate key present: {config._id}')
            run_options[config._id] = config
            config_with_module_id[config._id] = module._id
    return list(run_options.values())

@live.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True, default_command=True, name="deploy")
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
@click.option("--brokerage",
              type=click.Choice([b.get_name() for b in all_local_brokerages], case_sensitive=False),
              help="The brokerage to use")
@click.option("--data-feed",
              type=click.Choice([d.get_name() for d in all_local_data_feeds], case_sensitive=False),
              multiple=True,
              help="The data feed to use")
@click.option("--data-provider",
              type=click.Choice([dp.get_name() for dp in all_data_providers], case_sensitive=False),
              help="Update the Lean configuration file to retrieve data from the given provider")
@options_from_json(_get_configs_for_options())
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
def deploy(project: Path,
        environment: Optional[str],
        output: Optional[Path],
        detach: bool,
        brokerage: Optional[str],
        data_feed: Optional[str],
        data_provider: Optional[str],
        release: bool,
        image: Optional[str],
        update: bool,
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
    # Reset globals so we reload everything in between tests
    global _cached_organizations
    _cached_organizations = None
    global _cached_lean_config
    _cached_lean_config = None

    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "live" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_config_manager = container.lean_config_manager()

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
            environment_name: copy.copy(_environment_skeleton)
        }

        [brokerage_configurer] = [_get_and_build_module(brokerage, all_local_brokerages, kwargs)]
        brokerage_configurer.configure(lean_config, environment_name)

        for df in data_feed:
            [data_feed_configurer] = [_get_and_build_module(df, all_local_data_feeds, kwargs)]
            data_feed_configurer.configure(lean_config, environment_name)

    else:
        environment_name = "lean-cli"
        lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)
        _configure_lean_config_interactively(lean_config, environment_name)

    if data_provider is not None:
        [data_provider_configurer] = [_get_and_build_module(data_provider, all_data_providers, kwargs)]
        data_provider_configurer.configure(lean_config, environment_name)

    if "environments" not in lean_config or environment_name not in lean_config["environments"]:
        lean_config_path = lean_config_manager.get_lean_config_path()
        raise MoreInfoError(f"{lean_config_path} does not contain an environment named '{environment_name}'",
                            "https://www.lean.io/docs/lean-cli/live-trading")

    if not lean_config["environments"][environment_name]["live-mode"]:
        raise MoreInfoError(f"The '{environment_name}' is not a live trading environment (live-mode is set to false)",
                            "https://www.lean.io/docs/lean-cli/live-trading")

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

    lean_runner = container.lean_runner()
    lean_runner.run_lean(lean_config, environment_name, algorithm_file, output, engine_image, None, release, detach)
