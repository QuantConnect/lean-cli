import itertools
import json
import os
import platform
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import click
from docker.types import Mount

from lean.config.global_config import GlobalConfig
from lean.config.local_config import get_lean_config, get_lean_config_path
from lean.constants import CREDENTIALS_FILE_NAME
from lean.decorators import local_command
from lean.docker import get_docker_client


# This command is based on the following files:
# https://github.com/QuantConnect/Lean/blob/254d0896f10b0fa3f50d178283bf94e34cb0b474/run_docker.sh
# https://github.com/QuantConnect/Lean/blob/254d0896f10b0fa3f50d178283bf94e34cb0b474/run_docker.bat

@local_command
@click.argument("project", type=click.Path(exists=True, file_okay=True, dir_okay=True, resolve_path=True))
@click.option("--output", "-o",
              type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
              help="Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP")
def backtest(project: str, output: str) -> None:
    """Backtest a project locally using Docker.

    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be used.

    If PROJECT is a file, the algorithm in the specified file will be used."""
    # Parse which directory contains the source files and which source file contains the algorithm
    project_arg = Path(project)
    algorithm_file = None

    if project_arg.is_file():
        project_dir = project_arg.parent
        algorithm_file = project_arg
    else:
        project_dir = project_arg

        for candidate_algorithm_file in [project_dir / "main.py", project_dir / "Main.cs"]:
            if candidate_algorithm_file.exists():
                algorithm_file = candidate_algorithm_file
                break

        if algorithm_file is None:
            raise click.ClickException("The specified project does not contain a main.py or Main.cs file")

    # Set up the output directory to store the results in
    if output is not None:
        output_dir = Path(output)
    else:
        output_dir = project_dir / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir.mkdir(parents=True)

    # Retrieve the Lean config and add the properties which are removed in `lean init`
    lean_config = get_lean_config()
    lean_config["environment"] = "backtesting"
    lean_config["composer-dll-directory"] = "."
    lean_config["debugging"] = False
    lean_config["debugging-method"] = "LocalCmdline"

    credentials_config = GlobalConfig(CREDENTIALS_FILE_NAME)
    lean_config["job-user-id"] = credentials_config["user_id"] if "user_id" in credentials_config else "0"
    lean_config["api-access-token"] = credentials_config["api_token"] if "api_token" in credentials_config else ""

    if algorithm_file.name.endswith(".py"):
        lean_config["algorithm-type-name"] = algorithm_file.name.split(".")[0]
        lean_config["algorithm-language"] = "Python"
        lean_config["algorithm-location"] = f"../../../../Project/{algorithm_file.name}"
    else:
        with open(algorithm_file) as file:
            lean_config["algorithm-type-name"] = re.findall(f"class ([a-zA-Z0-9]+)", file.read())[0]
        lean_config["algorithm-language"] = "CSharp"
        lean_config["algorithm-location"] = "QuantConnect.Algorithm.CSharp.dll"

    # Write the complete Lean config to a temporary file because we only need it for this single backtest
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as config_file:
        json.dump(lean_config, config_file, indent=4)
        config_path = config_file.name

    # The dict containing all options passed to `docker run`
    # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
    run_options: Dict[str, Any] = {
        "detach": True,
        "mounts": [Mount(target="/Lean/Launcher/config.json", source=config_path, type="bind", read_only=True)],
        "volumes": {},
        "ports": {
            "5678": "5678",
            "6000": "6000"
        }
    }

    # Mount the data directory
    lean_project_root = get_lean_config_path().parent
    data_dir = lean_project_root / lean_config["data-folder"]
    run_options["volumes"][str(data_dir)] = {
        "bind": "/Data",
        "mode": "ro"
    }

    # Mount the output directory
    run_options["volumes"][str(output_dir)] = {
        "bind": "/Results",
        "mode": "rw"
    }

    # Make sure host.docker.internal resolves on Linux
    # See https://github.com/QuantConnect/Lean/pull/5092
    if platform.system() == "Linux":
        run_options["extra_hosts"] = {
            "host.docker.internal": "172.17.0.1"
        }

    # Mount the project which needs to be backtested
    run_options["volumes"][str(project_dir)] = {
        "bind": "/Project",
        "mode": "rw"
    }

    # TODO: Compile C# projects before running them

    # Configure the image and command to run
    docker_image = "quantconnect/lean"
    docker_tag = "latest"
    command = "--data-folder /Data --results-destination-folder /Results --config /Lean/Launcher/config.json"

    docker_client = get_docker_client()

    # Pull the image if it hasn't been downloaded yet
    installed_tags = list(itertools.chain(*[x.tags for x in docker_client.images.list()]))
    if f"{docker_image}:{docker_tag}" not in installed_tags:
        click.echo(f"Pulling {docker_image}:{docker_tag} from Docker Hub, this may take a while...")

        # We cannot really use docker_client.images.pull() here as it doesn't let us log the progress
        # Downloading 5+ GB without showing the progress does not provide a good developer experience
        # Since the pull command is the same on Windows, Linux and macOS we can safely use a system call
        os.system(f"docker image pull {docker_image}:{docker_tag}")

    # Run the backtest
    container = docker_client.containers.run(f"{docker_image}:{docker_tag}", command, **run_options)
    for line in container.logs(stream=True, follow=True):
        click.echo(line, nl=False)

    exit_code = container.wait()["StatusCode"]
    relative_project_dir = project_dir.relative_to(lean_project_root)
    relative_output_dir = output_dir.relative_to(lean_project_root)

    if exit_code == 0:
        click.echo(f"Successfully backtested '{relative_project_dir}' and stored the output in '{relative_output_dir}'")
    else:
        raise click.ClickException(
            f"Something went wrong while backtesting '{relative_project_dir}', the output is stored in '{relative_output_dir}'")
