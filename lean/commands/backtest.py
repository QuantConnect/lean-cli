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
from typing import List, Optional, Tuple
from click import command, option, argument, Choice

from lean.click import LeanCommand, PathParameter
from lean.constants import DEFAULT_ENGINE_IMAGE, LEAN_ROOT_PATH
from lean.container import container, Logger
from lean.models.utils import DebuggingMethod
from lean.models.cli import cli_data_downloaders, cli_addon_modules
from lean.components.util.json_modules_handler import build_and_configure_modules, non_interactive_config_build_for_name
from lean.models.click_options import options_from_json, get_configs_for_options

# The _migrate_* methods automatically update launch configurations for a given debugging method.
#
# Occasionally we make changes which require updated launch configurations.
# Projects which are created after these update have the correct configuration already,
# but projects created before that need changes.
#
# These methods checks if the project has outdated configurations, and if so, update them to keep it working.


def _migrate_python_pycharm(logger: Logger, project_dir: Path) -> None:
    from os import path
    from click import Abort

    workspace_xml_path = project_dir / ".idea" / "workspace.xml"
    if not workspace_xml_path.is_file():
        return

    xml_manager = container.xml_manager
    current_content = xml_manager.parse(workspace_xml_path.read_text(encoding="utf-8"))

    config = current_content.find('.//configuration[@name="Debug with Lean CLI"]')
    if config is None:
        return

    path_mappings = config.find('.//PathMappingSettings/option[@name="pathMappings"]/list')
    if path_mappings is None:
        return

    made_changes = False
    has_library_mapping = False

    library_dir = container.lean_config_manager.get_cli_root_directory() / "Library"

    if library_dir.is_dir():
        library_dir = f"$PROJECT_DIR$/{path.relpath(library_dir, project_dir)}".replace("\\", "/")
    else:
        library_dir = None

    for mapping in path_mappings.findall(".//mapping"):
        if mapping.get("local-root") == "$PROJECT_DIR$" and mapping.get("remote-root") == LEAN_ROOT_PATH:
            mapping.set("remote-root", "/LeanCLI")
            made_changes = True

        if library_dir is not None \
            and mapping.get("local-root") == library_dir \
            and mapping.get("remote-root") == "/Library":
            has_library_mapping = True

    if library_dir is not None and not has_library_mapping:
        library_mapping = xml_manager.parse("<mapping/>")
        library_mapping.set("local-root", library_dir)
        library_mapping.set("remote-root", "/Library")
        path_mappings.append(library_mapping)
        made_changes = True

    if made_changes:
        workspace_xml_path.write_text(xml_manager.to_string(current_content), encoding="utf-8")

        logger = container.logger
        logger.warn("Your run configuration has been updated to work with the latest version of LEAN")
        logger.warn("Please restart the debugger in PyCharm and run this command again")

        raise Abort()


def _migrate_python_vscode(project_dir: Path) -> None:
    from json import dumps, loads
    launch_json_path = project_dir / ".vscode" / "launch.json"
    if not launch_json_path.is_file():
        return

    current_content = loads(launch_json_path.read_text(encoding="utf-8"))
    if "configurations" not in current_content or not isinstance(current_content["configurations"], list):
        return

    config = next((c for c in current_content["configurations"] if c["name"] == "Debug with Lean CLI"), None)
    if config is None:
        return

    made_changes = False
    has_library_mapping = False

    library_dir = container.lean_config_manager.get_cli_root_directory() / "Library"
    if not library_dir.is_dir():
        library_dir = None

    for mapping in config["pathMappings"]:
        if mapping["localRoot"] == "${workspaceFolder}" and mapping["remoteRoot"] == LEAN_ROOT_PATH:
            mapping["remoteRoot"] = "/LeanCLI"
            made_changes = True

        if library_dir is not None and mapping["localRoot"] == str(library_dir) and mapping["remoteRoot"] == "/Library":
            has_library_mapping = True

    if library_dir is not None and not has_library_mapping:
        config["pathMappings"].append({
            "localRoot": str(library_dir),
            "remoteRoot": "/Library"
        })
        made_changes = True

    if made_changes:
        launch_json_path.write_text(dumps(current_content, indent=4), encoding="utf-8")


def _migrate_csharp_rider(logger: Logger, project_dir: Path) -> None:
    from click import Abort

    made_changes = False
    xml_manager = container.xml_manager

    for dir_name in [f".idea.{project_dir.stem}", f".idea.{project_dir.stem}.dir"]:
        workspace_xml_path = project_dir / ".idea" / dir_name / ".idea" / "workspace.xml"
        if not workspace_xml_path.is_file():
            continue

        current_content = xml_manager.parse(workspace_xml_path.read_text(encoding="utf-8"))

        run_manager = current_content.find(".//component[@name='RunManager']")
        if run_manager is None:
            continue

        config = run_manager.find(".//configuration[@name='Debug with Lean CLI']")
        if config is None:
            continue

        run_manager.remove(config)

        workspace_xml_path.write_text(xml_manager.to_string(current_content), encoding="utf-8")
        made_changes = True

    if container.project_manager.generate_rider_config(project_dir) or made_changes:
        logger.warn("Your debugger configuration has been updated to work with the latest version of LEAN")
        logger.warn("Please restart Rider and start debugging again")
        logger.warn(
            "See https://www.lean.io/docs/v2/lean-cli/backtesting/debugging#05-C-and-Rider for the updated instructions")

        raise Abort()


def _migrate_csharp_vscode(project_dir: Path) -> None:
    from json import dumps, loads
    launch_json_path = project_dir / ".vscode" / "launch.json"
    if not launch_json_path.is_file():
        return

    current_content = loads(launch_json_path.read_text(encoding="utf-8"))
    if "configurations" not in current_content or not isinstance(current_content["configurations"], list):
        return

    config = next((c for c in current_content["configurations"] if c["name"] == "Debug with Lean CLI"), None)
    if config is None:
        return

    if config["type"] != "mono" and config["processId"] != "${command:pickRemoteProcess}":
        return

    config.pop("address", None)
    config.pop("port", None)

    config["type"] = "coreclr"
    config["processId"] = "1"

    config["pipeTransport"] = {
        "pipeCwd": "${workspaceRoot}",
        "pipeProgram": "docker",
        "pipeArgs": ["exec", "-i", "lean_cli_vsdbg"],
        "debuggerPath": "/root/vsdbg/vsdbg",
        "quoteArgs": False
    }

    config["logging"] = {
        "moduleLoad": False
    }

    launch_json_path.write_text(dumps(current_content, indent=4), encoding="utf-8")


def _migrate_csharp_csproj(project_dir: Path) -> None:
    csproj_path = next((f for f in project_dir.rglob("*.csproj")), None)
    if csproj_path is None:
        return

    xml_manager = container.xml_manager

    current_content = xml_manager.parse(csproj_path.read_text(encoding="utf-8"))
    if current_content.find(".//PropertyGroup/DefaultItemExcludes") is not None:
        return

    property_group = current_content.find(".//PropertyGroup")
    if property_group is None:
        property_group = xml_manager.parse("<PropertyGroup/>")
        current_content.append(property_group)

    default_item_excludes = xml_manager.parse(
        "<DefaultItemExcludes>$(DefaultItemExcludes);backtests/*/code/**;live/*/code/**;optimizations/*/code/**</DefaultItemExcludes>")
    property_group.append(default_item_excludes)

    csproj_path.write_text(xml_manager.to_string(current_content), encoding="utf-8")


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP)")
@option("--detach", "-d",
              is_flag=True,
              default=False,
              help="Run the backtest in a detached Docker container and return immediately")
@option("--debug",
              type=Choice(["pycharm", "ptvsd", "debugpy", "vsdbg", "rider", "local-platform"], case_sensitive=False),
              help="Enable a certain debugging method (see --help for more information)")
@option("--data-provider-historical",
              type=Choice([dp.get_name() for dp in cli_data_downloaders], case_sensitive=False),
              default="Local",
              help="Update the Lean configuration file to retrieve data from the given historical provider")
@options_from_json(get_configs_for_options("backtest"))
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
@option("--python-venv",
              type=str,
              help=f"The path of the python virtual environment to be used")
@option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN engine image before running the backtest")
@option("--backtest-name",
              type=str,
              help="Backtest name")
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
def backtest(project: Path,
             output: Optional[Path],
             detach: bool,
             debug: Optional[str],
             data_provider_historical: Optional[str],
             download_data: bool,
             data_purchase_limit: Optional[int],
             release: bool,
             image: Optional[str],
             python_venv: Optional[str],
             update: bool,
             backtest_name: str,
             addon_module: Optional[List[str]],
             extra_config: Optional[Tuple[str, str]],
             extra_docker_config: Optional[str],
             no_update: bool,
             **kwargs) -> None:
    """Backtest a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    Go to the following url to learn how to debug backtests locally using the Lean CLI:
    https://www.lean.io/docs/v2/lean-cli/backtesting/debugging

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    from datetime import datetime
    from json import loads

    logger = container.logger
    project_manager = container.project_manager
    algorithm_file = project_manager.find_algorithm_file(Path(project))
    lean_config_manager = container.lean_config_manager
    if output is None:
        output = algorithm_file.parent / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    environment_name = "backtesting"
    debugging_method = None
    if debug == "pycharm":
        debugging_method = DebuggingMethod.PyCharm
        _migrate_python_pycharm(logger, algorithm_file.parent)
    elif debug == "ptvsd":
        debugging_method = DebuggingMethod.PTVSD
        _migrate_python_vscode(algorithm_file.parent)
        logger.warn("The PTVSD debugging method is deprecated and might be removed in a future version of LEAN. "
                    "Consider using DebugPy instead.")
    elif debug == "debugpy":
        debugging_method = DebuggingMethod.DebugPy
        _migrate_python_vscode(algorithm_file.parent)
    elif debug == "vsdbg":
        debugging_method = DebuggingMethod.VSDBG
        _migrate_csharp_vscode(algorithm_file.parent)
    elif debug == "rider":
        debugging_method = DebuggingMethod.Rider
        _migrate_csharp_rider(logger, algorithm_file.parent)
    elif debug == "local-platform":
        debugging_method = DebuggingMethod.LocalPlatform

    if detach and debugging_method != None and debugging_method != DebuggingMethod.LocalPlatform:
        raise RuntimeError("Running a debugging session in a detached container is not supported")

    if algorithm_file.name.endswith(".cs"):
        _migrate_csharp_csproj(algorithm_file.parent)

    lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, debugging_method)

    if download_data:
        data_provider_historical = "QuantConnect"

    organization_id = container.organization_manager.try_get_working_organization_id()
    paths_to_mount = None

    engine_image, container_module_version, project_config = container.manage_docker_image(image, update, no_update,
                                                                                           algorithm_file.parent)

    if data_provider_historical is not None:
        data_provider = non_interactive_config_build_for_name(lean_config, data_provider_historical,
                                                              cli_data_downloaders, kwargs, logger, environment_name)
        data_provider.ensure_module_installed(organization_id, container_module_version)
        container.lean_config_manager.set_properties(data_provider.get_settings())
        paths_to_mount = data_provider.get_paths_to_mount()

    lean_config_manager.configure_data_purchase_limit(lean_config, data_purchase_limit)

    if not output.exists():
        output.mkdir(parents=True)

    # Set backtest name
    if backtest_name is not None and backtest_name != "":
        lean_config["backtest-name"] = backtest_name

    # Set extra config
    given_algorithm_id = None
    for key, value in extra_config:
        if key == "algorithm-id":
            given_algorithm_id = int(value)
        else:
            lean_config[key] = value

    output_config_manager = container.output_config_manager
    lean_config["algorithm-id"] = str(output_config_manager.get_backtest_id(output, given_algorithm_id))

    if python_venv is not None and python_venv != "":
        lean_config["python-venv"] = f'{"/" if python_venv[0] != "/" else ""}{python_venv}'

    # Configure addon modules
    build_and_configure_modules(addon_module, cli_addon_modules, organization_id, lean_config,
                                kwargs, logger, environment_name, container_module_version)

    lean_runner = container.lean_runner
    lean_runner.run_lean(lean_config,
                         environment_name,
                         algorithm_file,
                         output,
                         engine_image,
                         debugging_method,
                         release,
                         detach,
                         loads(extra_docker_config),
                         paths_to_mount)
