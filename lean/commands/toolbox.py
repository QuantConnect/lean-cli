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

import itertools
from pathlib import Path

import click

from lean.click import LeanCommand
from lean.constants import ENGINE_IMAGE
from lean.container import container


@click.command(cls=LeanCommand,
               requires_cli_project=True,
               context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.option("--toolbox-help", is_flag=True, default=False, help="Pass the --help flag to the ToolBox")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the selected LEAN engine version before running the ToolBox")
@click.option("--version",
              type=str,
              default="latest",
              help="The LEAN engine version to run the ToolBox in (defaults to the latest installed version)")
@click.pass_context
def toolbox(context: click.Context, toolbox_help: bool, update: bool, version: str) -> None:
    """Download, convert or generate data using one of the tools in Lean's ToolBox using Docker.

    \b
    All options are passed to the toolbox.
    Go to the following url to see the available apps and their supported options:
    https://github.com/QuantConnect/Lean/blob/master/ToolBox/README.md

    \b
    If a --source-dir or --source-meta-dir option is given, its value will be mounted as a volume in the Docker container.
    The --destination-dir option should be omitted, it'll automatically be set by the CLI.

    \b
    Example usage:
    $ lean toolbox --app=YahooDownloader --tickers=SPY,AAPL --resolution=Daily --from-date=19980102-00:00:00 --to-date=20210107-00:00:00
    """
    args = list(itertools.chain(*[arg.split("=") for arg in context.args]))
    if len(args) % 2 != 0:
        raise RuntimeError("Invalid options given")
    extra_options = {args[i]: args[i + 1] for i in range(0, len(args), 2)}

    lean_config_manager = container.lean_config_manager()
    data_dir = lean_config_manager.get_data_directory()
    lean_config_path = lean_config_manager.get_lean_config_path()

    run_options = {
        "entrypoint": ["mono", "QuantConnect.ToolBox.exe", "--destination-dir", "/Lean/Data"],
        "volumes": {
            str(data_dir): {
                "bind": "/Lean/Data",
                "mode": "rw"
            }
        }
    }

    if toolbox_help:
        run_options["entrypoint"].append("--help")

    for key, value in extra_options.items():
        # --destination-dir is automatically set by the CLI based on the data folder in the Lean config file
        if key == "--destination-dir":
            raise RuntimeError(
                f"Please configure the 'data-folder' in '{lean_config_path}' instead of setting --destination-dir")

        # --source-dir and --source-meta-dir specify directories which should be mounted into the container
        if key == "--source-dir" or key == "--source-meta-dir":
            path = Path(value).expanduser().resolve()

            if not path.is_dir():
                raise RuntimeError(f"The given value for '{key}' is not an existing directory")

            run_options["volumes"][str(path)] = {
                "bind": f"/Lean/Launcher/bin/Debug/{key.lstrip('--')}",
                "mode": "ro"
            }

            run_options["entrypoint"].extend([key, key.lstrip("--")])
            continue

        run_options["entrypoint"].extend([key, value])

    docker_manager = container.docker_manager()

    if version != "latest":
        if not docker_manager.tag_exists(ENGINE_IMAGE, version):
            raise RuntimeError("The specified version does not exist")

    if update:
        docker_manager.pull_image(ENGINE_IMAGE, version)

    success = docker_manager.run_image(ENGINE_IMAGE, version, **run_options)

    if not success:
        raise RuntimeError("Something went wrong while running the ToolBox")
