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

import json
from datetime import datetime
from pathlib import Path

from lean.commands.create_project import (DEFAULT_CSHARP_MAIN, DEFAULT_CSHARP_NOTEBOOK, DEFAULT_PYTHON_MAIN,
                                          DEFAULT_PYTHON_NOTEBOOK, LIBRARY_PYTHON_MAIN, LIBRARY_CSHARP_MAIN)
from lean.models.api import QCLanguage, QCLiveResults, QCProject, QCFullOrganization, \
    QCOrganizationData, QCOrganizationCredit, QCNode, QCNodeList, QCNodePrice


def _get_python_project_files(path: Path) -> dict:
    return {
        (path / "main.py"): DEFAULT_PYTHON_MAIN.replace("$CLASS_NAME$", "PythonProject"),
        (path / "research.ipynb"): DEFAULT_PYTHON_NOTEBOOK,
        (path / "config.json"): json.dumps({
            "algorithm-language": "Python",
            "parameters": {}
        }),
    }


def _get_csharp_project_files(path: Path) -> dict:
    return {
        (path / "Main.cs"): DEFAULT_CSHARP_MAIN.replace("$CLASS_NAME$", "CSharpProject"),
        (path / "research.ipynb"): DEFAULT_CSHARP_NOTEBOOK,
        (path / "config.json"): json.dumps({
            "algorithm-language": "CSharp",
            "parameters": {}
        }),
        (path / "CSharp Project.csproj"): """
        <Project Sdk="Microsoft.NET.Sdk">
            <PropertyGroup>
                <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
                <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
                <TargetFramework>net6.0</TargetFramework>
                <OutputPath>bin/$(Configuration)</OutputPath>
                <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
                <NoWarn>CS0618</NoWarn>
            </PropertyGroup>
            <ItemGroup>
                <PackageReference Include="QuantConnect.Lean" Version="2.5.11940" />
            </ItemGroup>
        </Project>
            """
    }


def _get_fake_libraries() -> dict:
    return {
        (Path.cwd() / "Library" / "Python Library" / "main.py"):
            LIBRARY_PYTHON_MAIN.replace("$CLASS_NAME$", "PythonLibrary"),
        (Path.cwd() / "Library" / "Python Library" / "research.ipynb"): DEFAULT_PYTHON_NOTEBOOK,
        (Path.cwd() / "Library" / "Python Library" / "config.json"): json.dumps({
            "algorithm-language": "Python",
            "parameters": {}
        }),
        (Path.cwd() / "Library" / "CSharp Library" / "Main.cs"):
            LIBRARY_CSHARP_MAIN.replace("$CLASS_NAME$", "CSharpLibrary"),
        (Path.cwd() / "Library" / "CSharp Library" / "research.ipynb"): DEFAULT_CSHARP_NOTEBOOK,
        (Path.cwd() / "Library" / "CSharp Library" / "config.json"): json.dumps({
            "algorithm-language": "CSharp",
            "parameters": {}
        }),
        (Path.cwd() / "Library" / "CSharp Library" / "CSharp Library.csproj"): """
    <Project Sdk="Microsoft.NET.Sdk">
        <PropertyGroup>
            <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
            <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
            <TargetFramework>net6.0</TargetFramework>
            <OutputPath>bin/$(Configuration)</OutputPath>
            <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
            <NoWarn>CS0618</NoWarn>
        </PropertyGroup>
        <ItemGroup>
            <PackageReference Include="QuantConnect.Lean" Version="2.5.11940" />
        </ItemGroup>
    </Project>
        """
    }


def _write_fake_directory(files: dict) -> None:
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w+") as file:
            file.write(content)


def create_fake_lean_cli_directory() -> None:
    """Creates a directory structure similar to the one created by `lean init` with a Python and a C# project,
    and a Python and a C# library"""
    (Path.cwd() / "data").mkdir()

    files = {
        (Path.cwd() / "lean.json"): """
{
    // data-folder documentation
    "data-folder": "data"
}
        """,
        **_get_python_project_files(Path.cwd() / "Python Project"),
        **_get_csharp_project_files(Path.cwd() / "CSharp Project"),
        **_get_fake_libraries()
    }

    _write_fake_directory(files)


def create_fake_lean_cli_directory_with_subdirectories(depth: int) -> None:
    """Creates a directory structure similar to the one created by `lean init` with a Python and a C# project,
    and a Python and a C# library"""
    (Path.cwd() / "data").mkdir()

    sub_dirs = Path('/'.join([f"Subdir{i}" for i in range(depth)]))
    python_project_dir = Path.cwd() / sub_dirs / "Python Project"
    csharp_project_dir = Path.cwd() / sub_dirs / "CSharp Project"

    files = {
        (Path.cwd() / "lean.json"): """
{
    // data-folder documentation
    "data-folder": "data"
}
        """,
        **_get_python_project_files(python_project_dir),
        **_get_csharp_project_files(csharp_project_dir),
        **_get_fake_libraries()
    }

    _write_fake_directory(files)


def create_api_project(id: int, name: str) -> QCProject:
    """Creates a fake API project response."""
    return QCProject(
        projectId=id,
        organizationId="123",
        name=name,
        description="Description",
        modified=datetime.now(),
        created=datetime.now(),
        language=QCLanguage.Python,
        collaborators=[],
        leanVersionId=10500,
        leanPinnedToMaster=True,
        parameters=[],
        liveResults=QCLiveResults(eStatus="Unknown"),
        libraries=[]
    )

def create_api_organization() -> QCFullOrganization:
    return QCFullOrganization(id="1",
                              name="a",
                              seats=1,
                              type="type",
                              credit=QCOrganizationCredit(movements=[], balance=1000000),
                              products=[],
                              data=QCOrganizationData(signedTime=None, current=False),
                              members=[])


def create_qc_nodes() -> QCNodeList:
    backtest = [QCNode(
        id="1",
        name="backtest",
        sku="backtest_test",
        busy=False,
        projectName="Python Project",
        description="test node",
        usedBy="Python Project",
        price=QCNodePrice(monthly=1, yearly=2),
        speed=0.1,
        cpu=1,
        ram=0.2,
        assets=1
    )]
    research = [QCNode(
        id="2",
        name="research",
        sku="research_test",
        busy=False,
        projectName="Python Project",
        description="test node",
        usedBy="Python Project",
        price=QCNodePrice(monthly=1, yearly=2),
        speed=0.1,
        cpu=1,
        ram=0.2,
        assets=2
    )]
    live = [QCNode(
        id="3",
        name="live",
        sku="live_test",
        busy=False,
        projectName="Python Project",
        description="test node",
        usedBy="Python Project",
        price=QCNodePrice(monthly=1, yearly=2),
        speed=0.1,
        cpu=1,
        ram=0.2,
        assets=3
    )]

    return QCNodeList(backtest=backtest, research=research, live=live)
