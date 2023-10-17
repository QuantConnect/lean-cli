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
from typing import List, Any, Tuple
from unittest import mock
import platform
import pytest

from lean.components.cloud.pull_manager import PullManager
from lean.components.config.storage import Storage
from lean.components.util.project_manager import ProjectManager
from lean.container import container
from lean.models.api import QCProject, QCLanguage, QCProjectLibrary
from tests.test_helpers import create_fake_lean_cli_directory, create_api_project, create_lean_environments
from tests.test_helpers import create_fake_lean_cli_project
from lean.components import forbidden_characters

def _create_pull_manager(api_client: mock.Mock,
                         project_config_manager: mock.Mock,
                         library_manager: mock.Mock = mock.Mock()) -> PullManager:
    logger = mock.Mock()
    platform_manager = mock.Mock()
    project_manager = container.project_manager
    organization_manager = container.organization_manager
    return PullManager(logger, api_client, project_manager,
                       project_config_manager, library_manager, platform_manager, organization_manager)


def _make_cloud_projects_and_libraries(project_count: int,
                                       library_count: int) -> Tuple[List[QCProject], List[QCProject]]:
    cloud_projects = [create_api_project(i, f"Project {i}") for i in range(1, project_count + 1)]
    libraries = [create_api_project(i, f"Library/Library {i - project_count}")
                 for i in range(project_count + 1, project_count + library_count + 1)]

    return cloud_projects, libraries


def _add_libraries_to_cloud_project(project: QCProject, libraries: List[QCProject], withAccess: bool = True) -> None:
    libraries = [QCProjectLibrary(projectId=library.projectId,
                                  libraryName=library.name,
                                  ownerName="Owner",
                                  access=withAccess)
                 for library in libraries]
    project.libraries.extend(libraries)


def _add_local_library_to_local_project(project_path: Path, library_path: Path) -> None:
    library_manager = container.library_manager
    library_manager.add_lean_library_to_project(project_path, library_path, False)


def _assert_pull_manager_adds_property_to_project_config(prop: str,
                                                         expected_value: Any,
                                                         cloud_projects: List[QCProject]) -> None:
    api_client = mock.Mock()
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())
    api_client.files.get_all = mock.MagicMock(return_value=[])

    def config_get_side_effect(key: str, default: Any = None):
        if key == "encryption-key-path":
            return None
        return []

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(side_effect=config_get_side_effect)
    project_config.set = mock.Mock()

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    pull_manager = _create_pull_manager(api_client, project_config_manager)
    pull_manager.pull_projects(cloud_projects, cloud_projects)

    project_config.set.assert_any_call(prop, expected_value)


def test_pull_manager_adds_lean_engine_version_to_config() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    project_id = 1000
    cloud_project = create_api_project(project_id, project_path.name)
    cloud_project.leanPinnedToMaster = False

    _assert_pull_manager_adds_property_to_project_config("lean-engine", cloud_project.leanVersionId, [cloud_project])


def test_pull_manager_adds_python_venv_to_config() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    project_id = 1000
    cloud_project = create_api_project(project_id, project_path.name)
    environments = create_lean_environments()
    environment = next(env for env in environments if env.path is not None)
    cloud_project.leanEnvironment = environment.id

    _assert_pull_manager_adds_property_to_project_config("python-venv", environment.id, [cloud_project])


def _assert_pull_manager_removes_property_from_project_config(prop: str, cloud_projects: List[QCProject]) -> None:
    api_client = mock.Mock()
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())
    api_client.files.get_all = mock.MagicMock(return_value=[])

    def config_get_side_effect(key: str, default: Any = None):
        if key == "encryption-key-path":
            return None
        return []

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(side_effect=config_get_side_effect)
    project_config.set = mock.Mock()
    project_config.delete = mock.Mock()

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    pull_manager = _create_pull_manager(api_client, project_config_manager)
    pull_manager.pull_projects(cloud_projects, cloud_projects)

    assert mock.call(prop) in project_config.delete.call_args_list
    assert prop not in [call.args[0] for call in project_config.set.call_args_list]


def test_pull_manager_removes_lean_engine_from_config_when_lean_pinned_to_master() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    config = Storage(str(project_path / "config.json"))
    config.set("lean-engine", 456)

    project_id = 1000
    cloud_project = create_api_project(project_id, project_path.name)
    cloud_project.leanPinnedToMaster = True

    _assert_pull_manager_removes_property_from_project_config("lean-engine", [cloud_project])


def test_pulls_libraries_referenced_by_the_project() -> None:
    create_fake_lean_cli_directory()

    cloud_projects, libraries = _make_cloud_projects_and_libraries(3, 5)
    cloud_projects.extend(libraries)

    test_project = cloud_projects[0]
    test_project_libraries = libraries[:2]
    _add_libraries_to_cloud_project(test_project, test_project_libraries)

    test_library = test_project_libraries[0]
    test_library_library = libraries[2]
    _add_libraries_to_cloud_project(test_library, [test_library_library])

    api_client = mock.Mock()
    api_client.files.get_all = mock.MagicMock(return_value=[])
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()

    pull_manager = _create_pull_manager(api_client, container.project_config_manager, library_manager)
    pull_manager.pull_projects([test_project], cloud_projects)

    api_client.files.get_all.assert_has_calls(
        [mock.call(test_project.projectId)] + [mock.call(library.projectId) for library in test_project.libraries] +
        [mock.call(library.projectId) for library in test_library.libraries],
        any_order=True)

    library_manager.add_lean_library_to_project.assert_has_calls(
        [mock.call(Path.cwd() / test_project.name, Path.cwd() / library.name, True)
         for library in test_project_libraries] +
        [mock.call(Path.cwd() / test_library.name, Path.cwd() / test_library_library.name, True)],
        any_order=True)
    library_manager.remove_lean_library_from_project.assert_not_called()


def test_pull_removes_library_references() -> None:
    create_fake_lean_cli_directory()

    cloud_projects, libraries = _make_cloud_projects_and_libraries(3, 5)
    cloud_projects.extend(libraries)

    test_project = create_api_project(1000, "Python Project")
    cloud_projects.append(test_project)

    # Add library reference to local project to test its removal
    project_path = Path.cwd() / "Python Project"
    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("cloud-id", test_project.projectId)
    library_path = Path.cwd() / "Library" / "Python Library"
    _add_local_library_to_local_project(project_path, library_path)

    api_client = mock.Mock()
    api_client.files.get_all = mock.MagicMock(return_value=[])
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()

    pull_manager = _create_pull_manager(api_client, container.project_config_manager, library_manager)
    pull_manager.pull_projects([test_project], cloud_projects)

    api_client.files.get_all.assert_called_once_with(test_project.projectId)

    library_manager.add_lean_library_to_project.assert_not_called()
    library_manager.remove_lean_library_from_project.assert_called_once_with(project_path, library_path, True)


def test_pull_adds_and_removes_library_references_simultaneously() -> None:
    create_fake_lean_cli_directory()

    cloud_projects, libraries = _make_cloud_projects_and_libraries(3, 5)
    cloud_projects.extend(libraries)

    test_project = create_api_project(1000, "Python Project")
    cloud_projects.append(test_project)

    # Add cloud libraries to cloud project to test additions
    test_project_libraries = libraries[:2]
    _add_libraries_to_cloud_project(test_project, test_project_libraries)

    # Add library reference to local project to test removal
    project_path = Path.cwd() / "Python Project"
    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("cloud-id", test_project.projectId)
    library_path = Path.cwd() / "Library" / "Python Library"
    _add_local_library_to_local_project(project_path, library_path)

    api_client = mock.Mock()
    api_client.files.get_all = mock.MagicMock(return_value=[])
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()

    pull_manager = _create_pull_manager(api_client, container.project_config_manager, library_manager)
    pull_manager.pull_projects([test_project], cloud_projects)

    api_client.files.get_all.assert_has_calls(
        [mock.call(test_project.projectId)] + [mock.call(library.projectId) for library in test_project.libraries],
        any_order=True)

    library_manager.add_lean_library_to_project.assert_has_calls(
        [mock.call(Path.cwd() / test_project.name, Path.cwd() / library.name, True)
         for library in test_project_libraries],
        any_order=True)
    library_manager.remove_lean_library_from_project.assert_called_once_with(project_path, library_path, True)


def test_pull_projects_restores_csharp_projects_and_its_libraries() -> None:
    create_fake_lean_cli_directory()

    cloud_projects, libraries = _make_cloud_projects_and_libraries(3, 5)
    cloud_projects.extend(libraries)

    test_project = cloud_projects[0]
    test_project.language = QCLanguage.CSharp
    test_project_libraries = libraries[:3]
    test_csharp_library1 = test_project_libraries[0]
    test_csharp_library1.language = QCLanguage.CSharp
    _add_libraries_to_cloud_project(test_project, test_project_libraries)

    test_csharp_library2 = libraries[3]
    test_csharp_library2.language = QCLanguage.CSharp
    _add_libraries_to_cloud_project(test_csharp_library1, [test_csharp_library2])

    api_client = mock.Mock()
    api_client.files.get_all = mock.MagicMock(return_value=[])
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()

    with mock.patch.object(ProjectManager, 'try_restore_csharp_project') as mock_try_restore_csharp_project:
        pull_manager = _create_pull_manager(api_client, container.project_config_manager, library_manager)
        pull_manager.pull_projects([test_project], cloud_projects)

    api_client.files.get_all.assert_has_calls(
        [mock.call(test_project.projectId)] + [mock.call(library.projectId) for library in test_project.libraries] +
        [mock.call(library.projectId) for library in test_csharp_library1.libraries],
        any_order=True)

    library_manager.add_lean_library_to_project.assert_has_calls(
        [mock.call(Path.cwd() / test_project.name, Path.cwd() / library.name, True)
         for library in test_project_libraries] +
        [mock.call(Path.cwd() / test_csharp_library1.name, Path.cwd() / test_csharp_library2.name, True)],
        any_order=True)
    library_manager.remove_lean_library_from_project.assert_not_called()

    test_csharp_library1_path = Path.cwd() / test_csharp_library1.name
    test_csharp_library1_csproj_file_path = (test_csharp_library1_path / f"{test_csharp_library1_path.name}.csproj")

    test_csharp_library2_path = Path.cwd() / test_csharp_library2.name
    test_csharp_library2_csproj_file_path = (test_csharp_library2_path / f"{test_csharp_library2_path.name}.csproj")

    test_project_path = Path.cwd() / test_project.name
    test_project_csproj_file_path = (test_project_path / f"{test_project_path.name}.csproj")

    assert mock_try_restore_csharp_project.call_count == 3
    mock_try_restore_csharp_project.assert_has_calls([
        mock.call(test_csharp_library1_csproj_file_path),
        mock.call(test_csharp_library2_csproj_file_path),
        mock.call(test_project_csproj_file_path)
    ])


def test_pull_projects_updates_lean_config() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    api_client.files.get_all = mock.MagicMock(return_value=[])

    def config_get_side_effect(key: str, default: Any = None):
        if key == "encryption-key-path":
            return None
        return []

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(side_effect=config_get_side_effect)

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    library_manager = mock.Mock()

    pull_manager = _create_pull_manager(api_client, project_config_manager, library_manager)
    pull_manager.pull_projects(cloud_projects, cloud_projects)

    project_config.set.assert_has_calls([mock.call("python-venv", 1), mock.call("organization-id", "123")],
                                        any_order=True)


@pytest.mark.parametrize("unsupported_character", forbidden_characters)
def test_pull_projects_detects_unsupported_paths(unsupported_character: str) -> None:

    create_fake_lean_cli_directory()

    cloud_projects, libraries = _make_cloud_projects_and_libraries(3, 5)
    cloud_projects.extend(libraries)

    test_project = cloud_projects[0]
    expected_project_name_in_path = test_project.name
    test_project.name += unsupported_character

    test_project_libraries = libraries[:2]
    expected_library_names_in_paths = []
    for lib in test_project_libraries:
        expected_library_names_in_paths.append(lib.name)
        lib.name += unsupported_character
    _add_libraries_to_cloud_project(test_project, test_project_libraries)

    api_client = mock.Mock()
    api_client.files.get_all = mock.MagicMock(return_value=[])
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()

    pull_manager = _create_pull_manager(api_client, container.project_config_manager, library_manager)
    pull_manager.pull_projects([test_project], cloud_projects)

    api_client.files.get_all.assert_has_calls(
        [mock.call(test_project.projectId)] + [mock.call(library.projectId) for library in test_project.libraries],
        any_order=True)

    library_manager.add_lean_library_to_project.assert_has_calls(
        [mock.call(Path.cwd() / expected_project_name_in_path, Path.cwd() / library_name, True)
         for library_name in expected_library_names_in_paths],
        any_order=True)
    library_manager.remove_lean_library_from_project.assert_not_called()


@pytest.mark.parametrize("unsupported_character", forbidden_characters)
def test_push_projects_updates_name_in_cloud_if_required(unsupported_character: str) -> None:
    create_fake_lean_cli_directory()
    project_name = "Project 1"
    cloud_projects = [create_api_project(1, project_name + unsupported_character)]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    api_client.files.get_all = mock.MagicMock(return_value=[])

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(return_value=[])    # get("libraries")

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    library_manager = mock.Mock()

    pull_manager = _create_pull_manager(api_client, project_config_manager, library_manager)
    pull_manager.pull_projects(cloud_projects, cloud_projects)

    api_client.projects.update.assert_called_once()
    args, kwargs = api_client.projects.update.call_args
    assert "name" in kwargs and kwargs['name'] == project_name

@pytest.mark.parametrize("test_platform, unsupported_character", [
    *[("linux", char) for char in forbidden_characters],
    ("macos", ":")
])
def test_pull_projects_renames_project_if_required(test_platform: str, unsupported_character: str) -> None:

    if test_platform == "linux" and platform.system() != "Linux":
        pytest.skip("This test requires Linux")

    if test_platform == "macos" and platform.system() != "Darwin":
        pytest.skip("This test requires MacOS")

    project_name = "Project 1"
    unsupported_name  = project_name + unsupported_character
    cloud_projects = [create_api_project(1, unsupported_name)]
    create_fake_lean_cli_project(unsupported_name, "csharp")
    project_path = Path.cwd() / unsupported_name
    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("cloud-id", cloud_projects[0].projectId)
    assert (Path.cwd() / unsupported_name).exists()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    api_client.files.get_all = mock.MagicMock(return_value=[])
    api_client.projects.create = mock.MagicMock(return_value=cloud_projects[0])

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(return_value=[])

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    library_manager = mock.Mock()

    pull_manager = _create_pull_manager(api_client, project_config_manager, library_manager)
    pull_manager.pull_projects(cloud_projects, cloud_projects)

    assert not (Path.cwd() / unsupported_name).exists()
    assert (Path.cwd() / project_name).exists()


def test_pull_project_doesnt_pull_libraries_the_user_doesnt_have_access_to() -> None:
    create_fake_lean_cli_directory()

    cloud_projects, libraries = _make_cloud_projects_and_libraries(5, 15)
    cloud_projects.extend(libraries)

    test_project = cloud_projects[0]
    test_project_own_libraries = libraries[:2]
    _add_libraries_to_cloud_project(test_project, test_project_own_libraries)
    test_project_collab_libraries = libraries[2:4]
    _add_libraries_to_cloud_project(test_project, test_project_collab_libraries, False)

    test_library = test_project_own_libraries[0]
    test_library_own_libraries = libraries[4:6]
    _add_libraries_to_cloud_project(test_library, test_library_own_libraries)
    test_library_collab_libraries = libraries[4:6]
    _add_libraries_to_cloud_project(test_library, test_library_collab_libraries, False)

    def api_client_projects_get_side_effect(project_id: int, *args):
        return next(iter(x for x in cloud_projects if x.projectId == project_id))

    api_client = mock.Mock()
    api_client.files.get_all = mock.MagicMock(return_value=[])
    api_client.projects.get = mock.MagicMock(side_effect=api_client_projects_get_side_effect)

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()

    pull_manager = _create_pull_manager(api_client, container.project_config_manager, library_manager)
    pull_manager.pull_projects([test_project])

    api_client.files.get_all.assert_called()
    library_manager.add_lean_library_to_project.assert_has_calls(
        [mock.call(Path.cwd() / test_project.name, Path.cwd() / library.name, True)
         for library in test_project_own_libraries] +
        [mock.call(Path.cwd() / test_library.name, Path.cwd() / library.name, True)
         for library in test_library_own_libraries],
        any_order=True)
    library_manager.remove_lean_library_from_project.assert_not_called()
