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
from typing import Any, Dict, Optional, Tuple
from lean.constants import LEAN_STRICT_PYTHON_VERSION
from click import command, argument, option

from lean.click import LeanCommand, PathParameter
from lean.container import container
from lean.models.errors import MoreInfoError


def _get_nuget_package(name: str) -> Tuple[str, str]:
    """Retrieves the properly-capitalized name and the latest version of a package from NuGet.

    :param name: the name of the package, case in-sensitive
    :return: a tuple containing the proper name and latest version of the package, excluding pre-release versions
    """
    from json import loads
    http_client = container.http_client
    generic_error = RuntimeError(f"The NuGet API is not responding")

    service_index_response = http_client.get("https://api.nuget.org/v3/index.json", raise_for_status=False)
    if not service_index_response.ok:
        raise generic_error

    service_index = loads(service_index_response.text)
    query_url = next((x["@id"] for x in service_index["resources"] if x["@type"] == "SearchQueryService"), None)
    if query_url is None:
        raise generic_error

    query_response = http_client.get(f"{query_url}?q={name}&prerelease=false", raise_for_status=False)
    if not query_response.ok:
        raise generic_error

    query_results = loads(query_response.text)
    package_data = next((p for p in query_results["data"] if p["id"].lower() == name.lower()), None)

    if package_data is None:
        raise RuntimeError(f"NuGet does not have a package named {name}")

    return package_data["id"], package_data["versions"][-1]["version"]


def _add_csharp_package_to_csproj(csproj_file: Path, name: str, version: str) -> None:
    """Adds a NuGet package to a .csproj file, or updates the version if it is already added.

    :param csproj_file: the path to the .csproj file
    :param name: the name of the package
    :param version: the version of the package
    """
    from lxml import etree
    xml_manager = container.xml_manager
    csproj_tree = xml_manager.parse(csproj_file.read_text(encoding="utf-8"))

    existing_package_reference = csproj_tree.find(f".//PackageReference[@Include='{name}']")
    if existing_package_reference is not None:
        existing_package_reference.set("Version", version)
    else:
        last_item_group = csproj_tree.find(".//ItemGroup[last()]")
        if last_item_group is None:
            last_item_group = etree.SubElement(csproj_tree.find(".//Project"), "ItemGroup")

        last_item_group.append(etree.fromstring(f'<PackageReference Include="{name}" Version="{version}" />'))

    csproj_file.write_text(xml_manager.to_string(csproj_tree), encoding="utf-8")


def _add_nuget_package_to_csharp_project(project_dir: Path, name: str, version: Optional[str], no_local: bool) -> None:
    """Adds a NuGet package to the project in the given directory.

    Adds the library to the project's .csproj file, and restores the project if dotnet is on the user's PATH.

    :param project_dir: the path to the project directory
    :param name: the name of the library to add
    :param version: the version of the library to use, or None to pin to the latest version
    :param no_local: whether restoring the packages locally must be skipped
    """
    logger = container.logger

    if version is None:
        logger.info("Retrieving latest available version from NuGet")
        name, version = _get_nuget_package(name)

    project_manager = container.project_manager
    csproj_file = project_manager.get_csproj_file_path(project_dir)
    path_manager = container.path_manager
    logger.info(f"Adding {name} {version} to '{path_manager.get_relative_path(csproj_file)}'")

    original_csproj_content = csproj_file.read_text(encoding="utf-8")
    _add_csharp_package_to_csproj(csproj_file, name, version)
    project_manager.try_restore_csharp_project(csproj_file, original_csproj_content, no_local)


def _is_pypi_file_compatible(file: Dict[str, Any], required_python_version) -> bool:
    """Checks whether a file on PyPI is compatible with the Python version in the Docker images.

    :param file: the data of a file on PyPI, as returned by its JSON API
    :param required_python_version: the Python version to check compatibility for
    :return: True if the file is compatible with the given Python version, False if not
    """
    from pkg_resources import Requirement

    major, minor, patch = required_python_version.version
    if file["python_version"] not in [f"py{major}", f"py{major}{minor}", f"cp{major}", f"cp{major}{minor}", "source"]:
        return False

    if file["requires_python"] is not None:
        requires_python = file["requires_python"].rstrip(",")
        if str(required_python_version) not in Requirement.parse(f"python{requires_python}").specifier:
            return False

    return True


def _get_pypi_package(name: str, version: Optional[str]) -> Tuple[str, str]:
    """Retrieves the properly-capitalized name and the latest compatible version of a package from PyPI.

    If the version is already given, this method checks whether that version is compatible with the Docker images.

    :param name: the name of the package, case in-sensitive
    :param version: the version of the package
    :return: a tuple containing the proper name and latest compatible version of the package
    """
    from json import loads
    from dateutil.parser import isoparse
    from distutils.version import StrictVersion

    response = container.http_client.get(f"https://pypi.org/pypi/{name}/json", raise_for_status=False)

    if response.status_code == 404:
        raise RuntimeError(f"PyPI does not have a package named {name}")

    if not response.ok:
        raise RuntimeError(f"The PyPI API is not responding")

    pypi_data = loads(response.text)
    name = pypi_data["info"]["name"]

    required_python_version = StrictVersion(LEAN_STRICT_PYTHON_VERSION)

    last_compatible_version = None
    last_compatible_version_upload_time = None

    if version is not None:
        if version not in pypi_data["releases"]:
            raise RuntimeError(f"Version {version} of the {name} package does not exist")
        versions_to_check = {version: pypi_data["releases"][version]}
    else:
        versions_to_check = pypi_data["releases"]

    for version, files in versions_to_check.items():
        for file in files:
            if not _is_pypi_file_compatible(file, required_python_version):
                continue

            file_upload_time = isoparse(file["upload_time_iso_8601"])
            if last_compatible_version is None or file_upload_time >= last_compatible_version_upload_time:
                last_compatible_version = version
                last_compatible_version_upload_time = file_upload_time

    if last_compatible_version is None:
        if version is not None:
            raise RuntimeError(
                f"Version {version} of the {name} package is not compatible with Python {required_python_version}")
        else:
            raise RuntimeError(f"The {name} package is not compatible with Python {required_python_version}")

    return name, last_compatible_version


def _add_python_package_to_requirements(requirements_file: Path, name: str, version: str) -> None:
    """Adds a PyPI package to a requirements.txt file, or updates the version if it is already added.

    :param requirements_file: the path to the requirements.txt file (created if it does not exist yet)
    :param name: the name of the package
    :param version: the version of the package
    """
    from pkg_resources import Requirement

    if not requirements_file.is_file():
        requirements_file.touch()

    requirements_lines = requirements_file.read_text(encoding="utf-8").splitlines()

    new_lines = []
    requirement_added = False

    for line in requirements_lines:
        try:
            requirement = Requirement.parse(line)
            if requirement.name.lower() == name.lower():
                new_lines.append(f"{name}=={version}")
                requirement_added = True
            else:
                new_lines.append(line)
        except ValueError:
            new_lines.append(line)

    if not requirement_added:
        new_lines.append(f"{name}=={version}")

    new_content = "\n".join(new_lines).strip()
    new_content = new_content + "\n" if len(new_content) > 0 else new_content
    requirements_file.write_text(new_content, encoding="utf-8")


def _add_pypi_package_to_python_project(project_dir: Path, name: str, version: Optional[str], no_local: bool) -> None:
    """Adds a custom Python library to a Python project.

    Adds the library to the project's requirements.txt file,
    and installs it into the local Python environment to provide local autocomplete.

    :param project_dir: the path to the project directory
    :param name: the name of the library to add
    :param version: the version of the library to use, or None to pin to the latest version supporting Python 3.8
    :param no_local: whether installing the package in the local Python environment must be skipped
    """
    from subprocess import run
    from shutil import which
    logger = container.logger
    path_manager = container.path_manager

    if version is not None:
        logger.info(f"Checking compatibility of {name} {version} with the Python version used in the Docker images")
    else:
        logger.info("Retrieving latest compatible version from PyPI")

    name, version = _get_pypi_package(name, version)

    requirements_file = project_dir / "requirements.txt"
    logger.info(f"Adding {name} {version} to '{path_manager.get_relative_path(requirements_file)}'")

    _add_python_package_to_requirements(requirements_file, name, version)

    if not no_local and which("pip") is not None:
        logger.info(f"Installing {name} {version} in local Python environment to provide local autocomplete")

        process = run(["pip", "install", f"{name}=={version}"])

        if process.returncode != 0:
            raise RuntimeError(f"Something went wrong while installing {name} {version} "
                               "locally, see the logs above for more information")


@command(cls=LeanCommand)
@argument("project", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
@argument("name", type=str)
@option("--version", type=str, help="The version of the library to add (defaults to latest compatible version)")
@option("--no-local", is_flag=True, default=False, help="Skip making changes to your local environment")
def add(project: Path, name: str, version: Optional[str], no_local: bool) -> None:
    """Add a custom library to a project.

    PROJECT must be the path to the project.

    NAME must be either the name of a NuGet package (for C# projects), a PyPI package (for Python projects),
    or a path to a Lean CLI library.

    If --version is not given, and the library is a NuGet or PyPI package the package, it is pinned to the latest
    compatible version.
    For C# projects, this is the latest available version.
    For Python projects, this is the latest version compatible with Python 3.8 (which is what the Docker images use).
    For Lean CLI library projects, this is ignored.

    Custom C# libraries are added to your project's .csproj file,
    which is then restored if dotnet is on your PATH and the --no-local flag has not been given.

    Custom Python libraries are added to your project's requirements.txt file and are installed in your local Python
    environment so you get local autocomplete for the library. The last step can be skipped with the --no-local flag.

    \b
    C# example usage:
    $ lean library add "My CSharp Project" Microsoft.ML
    $ lean library add "My CSharp Project" Microsoft.ML --version 1.5.5
    $ lean library add "My CSharp Project" "Library/My CSharp Library"

    \b
    Python example usage:
    $ lean library add "My Python Project" tensorflow
    $ lean library add "My Python Project" tensorflow --version 2.5.0
    $ lean library add "My Python Project" "Library/My Python Library"
    """
    logger = container.logger
    project_config = container.project_config_manager.get_project_config(project)
    project_language = project_config.get("algorithm-language", None)

    if project_language is None:
        raise MoreInfoError(f"{project} is not a Lean CLI project",
                            "https://www.lean.io/docs/v2/lean-cli/projects/project-management#02-Create-Projects")

    library_manager = container.library_manager
    library_dir = Path(name).expanduser().resolve()

    if library_manager.is_lean_library(library_dir):
        logger.info(f"Adding Lean CLI library {library_dir} to project {project}")
        if project_language == "CSharp":
            library_manager.add_lean_library_to_csharp_project(project, library_dir, no_local)
        else:
            library_manager.add_lean_library_to_python_project(project, library_dir)
    else:
        logger.info(f"Adding package {name} to project {project}")
        if project_language == "CSharp":
            _add_nuget_package_to_csharp_project(project, name, version, no_local)
        else:
            _add_pypi_package_to_python_project(project, name, version, no_local)
