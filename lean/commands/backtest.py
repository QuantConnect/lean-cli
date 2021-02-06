import json
import platform
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import click
from docker.types import Mount

from lean.config.global_config import api_token_option, GlobalConfig, user_id_option
from lean.config.lean_config import get_lean_config, get_lean_config_path
from lean.constants import CREDENTIALS_FILE, LEAN_ENGINE_DOCKER_IMAGE, LEAN_ENGINE_DOCKER_TAG
from lean.decorators import local_command
from lean.docker import run_image


# This command is based on the following files:
# https://github.com/QuantConnect/Lean/blob/254d0896f10b0fa3f50d178283bf94e34cb0b474/run_docker.sh
# https://github.com/QuantConnect/Lean/blob/254d0896f10b0fa3f50d178283bf94e34cb0b474/run_docker.bat

def parse_project_paths(project: str) -> Tuple[Path, Path]:
    """Determine the path to the project containing the algorithm and the path to the algorithm itself.

    :param project: the project given by the user
    :return: a tuple containing the path to the project directory and the path to the algorithm file
    """
    project_path = Path(project)

    if project_path.is_file():
        return project_path.parent, project_path
    else:
        for candidate_algorithm_file in [project_path / "main.py", project_path / "Main.cs"]:
            if candidate_algorithm_file.exists():
                return project_path, candidate_algorithm_file

    raise click.ClickException("The specified project does not contain a main.py or Main.cs file")


def get_complete_lean_config(algorithm_file: Path) -> Dict[str, Any]:
    """Retrieve the Lean config stored in the Lean CLI project and fill it with the items removed in `lean init`.

    :param algorithm_file: the path to the file containing the algorithm to backtest
    :return: a full Lean config object containing all properties needed for Lean to run
    """
    lean_config = get_lean_config()
    lean_config["environment"] = "backtesting"
    lean_config["composer-dll-directory"] = "."
    lean_config["debugging"] = False
    lean_config["debugging-method"] = "LocalCmdline"

    credentials_config = GlobalConfig(CREDENTIALS_FILE)
    lean_config["job-user-id"] = user_id_option.get_value(default="0")
    lean_config["api-access-token"] = api_token_option.get_value(default="")

    if algorithm_file.name.endswith(".py"):
        lean_config["algorithm-type-name"] = algorithm_file.name.split(".")[0]
        lean_config["algorithm-language"] = "Python"
        lean_config["algorithm-location"] = f"../../../../Project/{algorithm_file.name}"
    else:
        with open(algorithm_file) as file:
            lean_config["algorithm-type-name"] = re.findall(f"class ([a-zA-Z0-9]+)", file.read())[0]
        lean_config["algorithm-language"] = "CSharp"
        lean_config["algorithm-location"] = "QuantConnect.Algorithm.CSharp.dll"

    return lean_config


def compile_csharp_project(project_dir: Path) -> Path:
    """Compile the C# project in the given directory and return the path where the binaries are stored.

    :param project_dir: the path to the directory containing C# files that needs to be compiled
    :return: the path to the directory containing the QuantConnect.Algorithm.CSharp.{dll,pdb} files
    """
    click.echo(f"Compiling the C# files in '{project_dir}'")

    # Create a temporary directory used for compiling the C# project
    compile_dir = Path(tempfile.mkdtemp())

    # Copy all project files to the temporary directory
    # shutil.copytree only works if the target directory doesn't exist yet, so we remove it before running copytree
    compile_dir.rmdir()
    shutil.copytree(project_dir, compile_dir)

    # Get a list of all dll's in the docker image
    _, output = run_image(LEAN_ENGINE_DOCKER_IMAGE, LEAN_ENGINE_DOCKER_TAG, "-c ls", True, entrypoint="bash")
    dlls = [line for line in output.split("\n") if line.endswith(".dll")]

    # Create a csproj file which will be used to compile the project
    with open(compile_dir / "Project.csproj", "w+") as file:
        references = [f"""
        <Reference Include="{dll.split('.dll')[0]}">
            <HintPath>/Lean/Launcher/bin/Debug/{dll}</HintPath>
        </Reference>
        """.strip() for dll in dlls]
        references = "\n".join(references)

        file.write(f"""
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <RootNamespace>QuantConnect.Algorithm.CSharp</RootNamespace>
        <AssemblyName>QuantConnect.Algorithm.CSharp</AssemblyName>
        <TargetFramework>net462</TargetFramework>
        <LangVersion>6</LangVersion>
        <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
        <OutputPath>bin/$(Configuration)/</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>
        <GenerateBindingRedirectsOutputType>true</GenerateBindingRedirectsOutputType>
    </PropertyGroup>
    <ItemGroup>
        {references}
    </ItemGroup>
</Project>
        """.strip())

    # Compile the project in a Docker container
    volumes = {
        str(compile_dir): {
            "bind": "/Project",
            "mode": "rw"
        }
    }

    success, _ = run_image(LEAN_ENGINE_DOCKER_IMAGE,
                           LEAN_ENGINE_DOCKER_TAG,
                           "restore /Project/Project.csproj",
                           False,
                           entrypoint="nuget", volumes=volumes)

    if not success:
        raise click.ClickException("Something went wrong while compiling your project")

    success, _ = run_image(LEAN_ENGINE_DOCKER_IMAGE,
                           LEAN_ENGINE_DOCKER_TAG,
                           "/Project/Project.csproj",
                           False,
                           entrypoint="msbuild",
                           volumes=volumes)

    if not success:
        raise click.ClickException("Something went wrong while compiling your project")

    return compile_dir / "bin" / "Debug"


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
    project_dir, algorithm_file = parse_project_paths(project)

    # Set up the output directory to store the results in
    if output is not None:
        output_dir = Path(output)
    else:
        output_dir = project_dir / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir.mkdir(parents=True)

    # Retrieve the Lean config and add the properties which are removed in `lean init`
    lean_config = get_complete_lean_config(algorithm_file)

    # Write the complete Lean config to a temporary file because we only need it for this single backtest
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as config_file:
        json.dump(lean_config, config_file, indent=4)
        config_path = config_file.name

    # The dict containing all options passed to `docker run`
    # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
    run_options: Dict[str, Any] = {
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
    if algorithm_file.name.endswith(".py"):
        run_options["volumes"][str(project_dir)] = {
            "bind": "/Project",
            "mode": "rw"
        }
    else:
        # C# projects need to be compiled before the backtest can run
        csharp_binaries_dir = compile_csharp_project(project_dir)

        for extension in ["dll", "pdb"]:
            run_options["mounts"].append(
                Mount(target=f"/Lean/Launcher/bin/Debug/QuantConnect.Algorithm.CSharp.{extension}",
                      source=str(csharp_binaries_dir / f"QuantConnect.Algorithm.CSharp.{extension}"),
                      type="bind"))

    # Run the backtest and log the result
    command = "--data-folder /Data --results-destination-folder /Results --config /Lean/Launcher/config.json"
    success, _ = run_image(LEAN_ENGINE_DOCKER_IMAGE, LEAN_ENGINE_DOCKER_TAG, command, False, **run_options)

    relative_project_dir = project_dir.relative_to(lean_project_root)
    relative_output_dir = output_dir.relative_to(lean_project_root)

    if success:
        click.echo(f"Successfully backtested '{relative_project_dir}' and stored the output in '{relative_output_dir}'")
    else:
        raise click.ClickException(
            f"Something went wrong while backtesting '{relative_project_dir}', the output is stored in '{relative_output_dir}'")
