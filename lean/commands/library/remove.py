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

import shutil
import subprocess
from pathlib import Path
from typing import Union

import click
from pkg_resources import Requirement

from lean.click import LeanCommand, PathParameter
from lean.container import container
from lean.models.errors import MoreInfoError


def _remove_csharp_package(project_dir: Path, name: Union[str, Path], no_local: bool, is_lean_library: bool = False) -> None:
    """Removes a custom C# library from a C# project.

    Removes the library from the project's .csproj file,
    and restores the project if dotnet is on the user's PATH and no_local is False.

    :param project_dir: the path to the project directory
    :param name: the name of the NuGet package or path to the Lean CLI library to remove
    :param no_local: Whether restoring the packages locally must be skipped
    :param is_lean_library: Whether the library is a Lean CLI library
    """
    logger = container.logger()
    path_manager = container.path_manager()
    library_manager = container.library_manager()

    csproj_file = library_manager.get_csproj_file_path(project_dir)
    logger.info(f"Removing {name} from '{path_manager.get_relative_path(csproj_file)}'")

    xml_manager = container.xml_manager()
    csproj_tree = xml_manager.parse(csproj_file.read_text(encoding="utf-8"))

    xml_element_name = './/PackageReference'
    library_reference = name
    if is_lean_library:
        xml_element_name = './/ProjectReference'
        library_reference = library_manager.get_csharp_lean_library_path_for_csproj_file(project_dir, name)

    library_reference = library_reference.lower()
    for package_reference in csproj_tree.findall(xml_element_name):
        if package_reference.get("Include", "").lower() == library_reference:
            package_reference.getparent().remove(package_reference)

    csproj_file.write_text(xml_manager.to_string(csproj_tree), encoding="utf-8")

    if not no_local and shutil.which("dotnet") is not None:
        logger.info(f"Restoring packages in '{path_manager.get_relative_path(project_dir)}'")

        process = subprocess.run(["dotnet", "restore", str(csproj_file)], cwd=project_dir)

        if process.returncode != 0:
            raise RuntimeError("Something went wrong while restoring packages, see the logs above for more information")


def _remove_python_pypi_package(project_dir: Path, name: str) -> None:
    """Removes a custom Python library from a Python project.

    Removes the library from the project's requirements.txt file.

    :param project_dir: the path to the project directory
    :param name: the name of the library to remove
    """
    logger = container.logger()
    path_manager = container.path_manager()

    requirements_file = project_dir / "requirements.txt"
    logger.info(f"Removing {name} from '{path_manager.get_relative_path(requirements_file)}'")

    if not requirements_file.is_file():
        return

    requirements_content = requirements_file.read_text(encoding="utf-8")
    new_lines = []

    for line in requirements_content.splitlines():
        try:
            requirement = Requirement.parse(line)
            if requirement.name.lower() != name.lower():
                new_lines.append(line)
        except ValueError:
            new_lines.append(line)

    new_content = "\n".join(new_lines).strip()
    new_content = new_content + "\n" if len(new_content) > 0 else new_content
    requirements_file.write_text(new_content, encoding="utf-8")


def _remove_lean_library_reference_from_project(project_dir: Path, library_dir: Path) -> None:
    """Removed a Lean CLI library reference from a project.

    Removes the library path from the project's config.json

    :param project_dir: the path to the project directory
    :param library_dir: the path to the C# library directory
    """
    project_config = container.project_config_manager().get_project_config(project_dir)
    libraries = project_config.get("libraries", [])

    lean_config_manager = container.lean_config_manager()
    path_manager = container.path_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()
    library_relative_path = path_manager.get_relative_path(library_dir, lean_cli_root_dir).as_posix()

    libraries.remove(library_relative_path)
    project_config.set("libraries", libraries)


def _remove_csharp_lean_library(project_dir: Path, library_dir: Path, no_local: bool) -> None:
    """Removes a Lean CLI C# library from a C# project.

    Removes the library from the project's .csproj file,
    and restores the project if dotnet is on the user's PATH and no_local is False.

    :param project_dir: Path to the project directory
    :param library_dir: Path to the library directory
    :param no_local: Whether restoring the packages locally must be skipped
    """
    _remove_lean_library_reference_from_project(project_dir, library_dir)
    _remove_csharp_package(project_dir, library_dir, no_local, is_lean_library=True)


def _remove_python_lean_library(project_dir: Path, library_dir: Path) -> None:
    """Removes a Lean CLI Python library from a Python project.

    :param project_dir: Path to the project directory
    :param library_dir: Path to the library directory
    """
    _remove_lean_library_reference_from_project(project_dir, library_dir)


@click.command(cls=LeanCommand, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
@click.argument("name", type=str)
@click.option("--no-local", is_flag=True, default=False, help="Skip making changes to your local environment")
def remove(project: Path, name: str, no_local: bool) -> None:
    """Remove a custom library from a project.

    PROJECT must be the path to the project directory.

    NAME must be either the name of the NuGet package (for C# projects), the PyPI package (for Python projects),
    or the path to the Lean CLI library to remove.

    Custom C# libraries are removed from the project's .csproj file,
    which is then restored if dotnet is on your PATH and the --no-local flag has not been given.

    Custom Python libraries are removed from the project's requirements.txt file.

    \b
    C# example usage:
    $ lean library remove "My CSharp Project" Microsoft.ML

    \b
    Python example usage:
    $ lean library remove "My Python Project" tensorflow
    """
    project_config = container.project_config_manager().get_project_config(project)
    project_language = project_config.get("algorithm-language", None)

    if project_language is None:
        raise MoreInfoError(f"{project} is not a Lean CLI project",
                            "https://www.lean.io/docs/v2/lean-cli/projects/project-management#02-Create-Projects")

    library_manager = container.library_manager()
    library_dir = Path(name).expanduser().resolve()
    if library_manager.is_lean_library(library_dir):
        if project_language == "CSharp":
            _remove_csharp_lean_library(project, library_dir, no_local)
        else:
            _remove_python_lean_library(project, library_dir)
    else:
        if project_language == "CSharp":
            _remove_csharp_package(project, name, no_local, is_lean_library=False)
        else:
            _remove_python_pypi_package(project, name)
