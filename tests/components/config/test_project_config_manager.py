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

from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.xml_manager import XMLManager
from lean.models.config import CSharpLibrary
from tests.test_helpers import create_fake_lean_cli_directory


def test_get_project_config_returns_storage_instance_of_correct_file() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = ProjectConfigManager(XMLManager())
    project_config = project_config_manager.get_project_config(Path.cwd() / "Python Project")

    assert project_config.file == Path.cwd() / "Python Project" / "config.json"


def test_get_local_id_returns_unique_id_per_project() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = ProjectConfigManager(XMLManager())

    python_id = project_config_manager.get_local_id(Path.cwd() / "Python Project")
    csharp_id = project_config_manager.get_local_id(Path.cwd() / "CSharp Project")

    assert python_id != csharp_id


def test_get_local_id_returns_same_id_for_project_when_called_multiple_times() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = ProjectConfigManager(XMLManager())

    ids = []
    for _ in range(5):
        ids.append(project_config_manager.get_local_id(Path.cwd() / "Python Project"))

    assert len(set(ids)) == 1


def test_get_csharp_libraries_returns_all_libraries_in_package_reference_tags_in_csproj() -> None:
    create_fake_lean_cli_directory()

    with (Path.cwd() / "CSharp Project" / "CSharp Project.csproj").open("w+", encoding="utf-8") as file:
        file.write("""
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <TargetFramework>net5.0</TargetFramework>
        <LangVersion>9</LangVersion>
        <OutputPath>bin/$(Configuration)</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <NoWarn>CS0618</NoWarn>
    </PropertyGroup>
    <ItemGroup>
        <PackageReference Include="QuantConnect.Lean" Version="2.5.11586"/>
        <PackageReference Include="Microsoft.ML" Version="1.5.5"/>
        <PackageReference Include="LibTopoART" Version="0.94.0"/>
    </ItemGroup>
</Project>
        """)

    project_config_manager = ProjectConfigManager(XMLManager())
    libraries = project_config_manager.get_csharp_libraries(Path.cwd() / "CSharp Project")

    assert len(libraries) == 3
    assert CSharpLibrary(name="QuantConnect.Lean", version="2.5.11586") in libraries
    assert CSharpLibrary(name="Microsoft.ML", version="1.5.5") in libraries
    assert CSharpLibrary(name="LibTopoART", version="0.94.0") in libraries


def test_get_csharp_libraries_returns_empty_list_when_no_csproj_in_project_directory() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = ProjectConfigManager(XMLManager())

    assert len(project_config_manager.get_csharp_libraries(Path.cwd() / "Python Project")) == 0


def test_get_csharp_libraries_skips_invalid_package_reference_tags() -> None:
    create_fake_lean_cli_directory()

    with (Path.cwd() / "CSharp Project" / "CSharp Project.csproj").open("w+", encoding="utf-8") as file:
        file.write("""
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <TargetFramework>net5.0</TargetFramework>
        <LangVersion>9</LangVersion>
        <OutputPath>bin/$(Configuration)</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <NoWarn>CS0618</NoWarn>
    </PropertyGroup>
    <ItemGroup>
        <PackageReference Include="QuantConnect.Lean" Version="2.5.11586"/>
        <PackageReference Include="Microsoft.ML"/>
        <PackageReference Version="0.94.0"/>
        <PackageReference/>
    </ItemGroup>
</Project>
        """)

    project_config_manager = ProjectConfigManager(XMLManager())
    libraries = project_config_manager.get_csharp_libraries(Path.cwd() / "CSharp Project")

    assert len(libraries) == 1
    assert CSharpLibrary(name="QuantConnect.Lean", version="2.5.11586") in libraries
