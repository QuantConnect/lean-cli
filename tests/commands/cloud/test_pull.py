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
from typing import Tuple, List
from unittest import mock

from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.components.cloud.pull_manager import PullManager
from lean.container import container
from lean.models.api import QCProject
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory


def _make_cloud_projects_and_libraries(project_count: int, library_count: int) -> Tuple[List[QCProject], List[QCProject]]:
    cloud_projects = [create_api_project(i, f"Project {i}") for i in range(1, project_count + 1)]
    libraries = [create_api_project(i, f"Library/Library {i - project_count}")
                 for i in range(project_count + 1, project_count + library_count + 1)]

    return cloud_projects, libraries


def _add_libraries_to_cloud_project(project: QCProject, libraries: List[QCProject]) -> None:
    libraries_ids = [library.projectId for library in libraries]
    project.libraries.extend(libraries_ids)


def _add_local_library_to_local_project(project_path: Path, library_path: Path) -> None:
    library_manager = container.library_manager()
    library_manager.add_lean_library_to_project(project_path, library_path, False)


def test_cloud_pull_pulls_all_non_bootcamp_projects_when_no_options_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with(cloud_projects[:3])


def test_cloud_pull_pulls_all_projects_when_pull_bootcamp_option_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--pull-bootcamp"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with(cloud_projects)


def test_cloud_pull_pulls_project_by_id() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "1"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with([cloud_projects[0]])


def test_cloud_pull_pulls_project_by_name() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "Project 1"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with([cloud_projects[0]])


def test_cloud_pull_aborts_when_project_input_matches_no_cloud_projects() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "Project 4"])

    assert result.exit_code != 0

    pull_manager.pull_projects.assert_not_called()


def test_cloud_pull_updates_lean_config() -> None:
    create_fake_lean_cli_directory()

    def my_side_effect(*args, **kwargs):
        return True

    cloud_projects = [create_api_project(1, "Project 1")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    project_config = mock.Mock()

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    project_manager = mock.Mock()
    project_manager.get_source_files = mock.MagicMock(return_value=[])

    platform_manager = mock.Mock()
    container.platform_manager.override(providers.Object(platform_manager))

    pull_manager = PullManager(mock.Mock(), api_client, project_manager, project_config_manager, platform_manager)
    container.pull_manager.override(providers.Object(pull_manager))

    pull_manager.get_local_project_path = mock.MagicMock(side_effect=my_side_effect)
    pull_manager._pull_files = mock.MagicMock(side_effect=my_side_effect)

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "1"])

    assert result.exit_code == 0

    project_config.set.assert_called_with("organization-id", "123")


def test_pull_pulls_libraries_referenced_by_the_project() -> None:
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
    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)
    api_client.files.get_all = mock.MagicMock(return_value=[])
    container.api_client.override(providers.Object(api_client))

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()
    container.library_manager.override(providers.Object(library_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", test_project.projectId])

    assert result.exit_code == 0

    api_client.projects.get_all.assert_called_once()
    api_client.files.get_all.assert_has_calls(
        [mock.call(test_project.projectId)] + [mock.call(library_id) for library_id in test_project.libraries] +
        [mock.call(library_id) for library_id in test_library.libraries],
        any_order=True)

    lean_config_manager = container.lean_config_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()

    library_manager.add_lean_library_to_project.assert_has_calls(
        [mock.call(lean_cli_root_dir / test_project.name, lean_cli_root_dir / library.name, False)
         for library in test_project_libraries] +
        [mock.call(lean_cli_root_dir / test_library.name, lean_cli_root_dir / test_library_library.name, False)],
        any_order=True)
    library_manager.remove_lean_library_from_project.assert_not_called()


def test_pull_removes_library_references() -> None:
    create_fake_lean_cli_directory()

    cloud_projects, libraries = _make_cloud_projects_and_libraries(3, 5)
    cloud_projects.extend(libraries)

    test_project = create_api_project(1000, "Python Project")
    cloud_projects.append(test_project)

    lean_config_manager = container.lean_config_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()

    # Add library reference to local project to test its removal
    project_path = lean_cli_root_dir / "Python Project"
    library_path = lean_cli_root_dir / "Library" / "Python Library"
    _add_local_library_to_local_project(project_path, library_path)

    api_client = mock.Mock()
    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)
    api_client.files.get_all = mock.MagicMock(return_value=[])
    container.api_client.override(providers.Object(api_client))

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()
    container.library_manager.override(providers.Object(library_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", test_project.projectId])

    assert result.exit_code == 0

    api_client.projects.get_all.assert_called_once()
    api_client.files.get_all.assert_called_once_with(test_project.projectId)

    library_manager.add_lean_library_to_project.assert_not_called()
    library_manager.remove_lean_library_from_project.assert_called_once_with(project_path, library_path, False)


def test_pull_adds_and_removes_library_references_simultaneously() -> None:
    create_fake_lean_cli_directory()

    cloud_projects, libraries = _make_cloud_projects_and_libraries(3, 5)
    cloud_projects.extend(libraries)

    test_project = create_api_project(1000, "Python Project")
    cloud_projects.append(test_project)

    # Add cloud libraries to cloud project to test additions
    test_project_libraries = libraries[:2]
    _add_libraries_to_cloud_project(test_project, test_project_libraries)

    lean_config_manager = container.lean_config_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()

    # Add library reference to local project to test removal
    project_path = lean_cli_root_dir / "Python Project"
    library_path = lean_cli_root_dir / "Library" / "Python Library"
    _add_local_library_to_local_project(project_path, library_path)

    api_client = mock.Mock()
    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)
    api_client.files.get_all = mock.MagicMock(return_value=[])
    container.api_client.override(providers.Object(api_client))

    library_manager = mock.Mock()
    library_manager.add_lean_library_to_project = mock.Mock()
    library_manager.remove_lean_library_from_project = mock.Mock()
    container.library_manager.override(providers.Object(library_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", test_project.projectId])

    assert result.exit_code == 0

    api_client.projects.get_all.assert_called_once()
    api_client.files.get_all.assert_has_calls(
        [mock.call(test_project.projectId)] + [mock.call(library_id) for library_id in test_project.libraries],
        any_order=True)

    library_manager.add_lean_library_to_project.assert_has_calls(
        [mock.call(lean_cli_root_dir / test_project.name, lean_cli_root_dir / library.name, False)
         for library in test_project_libraries],
        any_order=True)
    library_manager.remove_lean_library_from_project.assert_called_once_with(project_path, library_path, False)

