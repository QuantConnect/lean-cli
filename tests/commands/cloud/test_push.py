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
from typing import Optional
from unittest import mock
from datetime import datetime

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.components.api.project_client import ProjectClient
from lean.components.cloud.push_manager import PushManager
from lean.container import container
from lean.models.api import QCFullFile, QCLanguage
from tests.test_helpers import create_fake_lean_cli_directory, create_api_project


def test_cloud_push_pushes_all_projects_when_no_options_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [
        create_api_project(1, "Python Project"),
        create_api_project(2, "CSharp Project"),
        create_api_project(3, "Library/Python Library"),
        create_api_project(4, "Library/CSharp Library")
    ]
    api_client = mock.Mock()
    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)
    container.api_client.override(providers.Object(api_client))

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once()
    args, kwargs = push_manager.push_projects.call_args

    expected_args = {
        Path.cwd() / "Python Project",
        Path.cwd() / "CSharp Project",
        Path.cwd() / "Library/Python Library",
        Path.cwd() / "Library/CSharp Library"
    }

    assert set(args[0]) == expected_args


def test_cloud_push_pushes_single_project_when_project_option_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Python Project")]
    api_client = mock.Mock()
    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)
    container.api_client.override(providers.Object(api_client))

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Python Project"], None)


def test_cloud_push_aborts_when_given_directory_is_not_lean_project() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_aborts_when_given_directory_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_removes_locally_removed_files_in_cloud() -> None:
    create_fake_lean_cli_directory()

    client = mock.Mock()
    fake_cloud_files = [QCFullFile(name="removed_file.py", content="", modified=datetime.now(), isLibrary=False)]
    client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)
    client.files.delete = mock.Mock()

    cloud_projects = [create_api_project(1, "Python Project")]
    client.projects.get_all = mock.MagicMock(return_value=cloud_projects)

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(side_effect=[1, "", {}])

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    project_manager = mock.Mock()
    project_manager.get_source_files = mock.MagicMock(return_value=[])

    push_manager = PushManager(mock.Mock(), client, project_manager, project_config_manager)
    container.push_manager.override(providers.Object(push_manager))
    container.api_client.override(providers.Object(client))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    project_config.get.assert_called()
    client.projects.get_all.assert_has_calls([mock.call(), mock.call()])
    project_manager.get_source_files.assert_called_once()
    project_config_manager.get_project_config.assert_called()
    client.files.get_all.assert_called_once()
    client.files.delete.assert_called_once()


@pytest.mark.parametrize("organization_id", ["d6e62db42593c72e67a534513413b692", None])
def test_cloud_push_creates_project_with_optional_organization_id(organization_id: Optional[str]) -> None:
    create_fake_lean_cli_directory()

    path = "Python Project"
    cloud_project = create_api_project(1, path)

    with mock.patch.object(ProjectClient, 'create', return_value=create_api_project(1, path)) as mock_create_project,\
         mock.patch.object(ProjectClient, 'get_all', side_effect=[[], [cloud_project]]) as mock_get_all_projects:
        organization_id_option = ["--organization-id", organization_id] if organization_id is not None else []
        result = CliRunner().invoke(lean, ["cloud", "push", "--project", path, *organization_id_option])

    assert result.exit_code == 0

    mock_get_all_projects.assert_has_calls([mock.call(), mock.call()])
    mock_create_project.assert_called_once_with(path, QCLanguage.Python, organization_id)


def test_cloud_push_updates_lean_config() -> None:

    create_fake_lean_cli_directory()

    def my_side_effect(*args, **kwargs):
        return "Python"

    cloud_project = create_api_project(1, "Python Project")
    api_client = mock.Mock()
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="removed_file.py", content="", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)
    api_client.files.delete = mock.Mock()

    api_client.projects.get_all = mock.MagicMock(return_value=[cloud_project])
    api_client.projects.get = mock.MagicMock(return_value=create_api_project(1, "Python Project"))

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(side_effect=my_side_effect)

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    project_manager = mock.Mock()
    project_manager.get_source_files = mock.MagicMock(return_value=[])

    push_manager = PushManager(mock.Mock(), api_client, project_manager, project_config_manager)
    container.push_manager.override(providers.Object(push_manager))
    container.api_client.override(providers.Object(api_client))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    project_config.set.assert_called_with("organization-id", "123")


def test_cloud_push_pushes_libraries_referenced_by_the_project() -> None:
    create_fake_lean_cli_directory()

    lean_config_manager = container.lean_config_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()

    project_path = lean_cli_root_dir / "Python Project"
    python_library_path = lean_cli_root_dir / "Library/Python Library"
    csharp_library_path = lean_cli_root_dir / "Library/CSharp Library"

    # library_manager = container.library_manager()
    # library_manager.add_lean_library_reference_to_project(python_library_path, csharp_library_path)

    push_manager = mock.Mock()
    push_manager.push_projects = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    api_client = mock.Mock()
    api_client.projects.add_library = mock.Mock()
    api_client.projects.delete_library = mock.Mock()

    cloud_projects = [create_api_project(i, f"Project {i}") for i in range(1, 6)]
    project_id = 1000
    python_library_id = 1001
    csharp_library_id = 1002
    cloud_projects.append(create_api_project(project_id, project_path.name))
    cloud_projects.append(create_api_project(python_library_id,
                                             str(python_library_path.relative_to(lean_cli_root_dir))))
    cloud_projects.append(create_api_project(csharp_library_id,
                                             str(csharp_library_path.relative_to(lean_cli_root_dir))))
    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)

    container.api_client.override(providers.Object(api_client))

    project_config = mock.Mock()
    project_config.file.exists = mock.MagicMock(return_value=True)
    project_config.get = mock.MagicMock(return_value=[{
        "name": python_library_path.name,
        "path": str(python_library_path.relative_to(lean_cli_root_dir))
    }])

    python_library_config = mock.Mock()
    python_library_libraries = [{
        "name": csharp_library_path.name,
        "path": str(csharp_library_path.relative_to(lean_cli_root_dir))
    }]
    python_library_config.get = mock.MagicMock(side_effect=[python_library_libraries,
                                                            str(python_library_id),
                                                            python_library_libraries])

    csharp_library_config = mock.Mock()
    csharp_library_config.get = mock.MagicMock(side_effect=[[], str(csharp_library_id), []])

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(side_effect=[project_config,
                                                                            project_config,
                                                                            python_library_config,
                                                                            csharp_library_config,
                                                                            project_config,
                                                                            python_library_config,
                                                                            python_library_config,
                                                                            csharp_library_config,
                                                                            csharp_library_config])
    container.project_config_manager.override(providers.Object(project_config_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path.name])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once_with([project_path, python_library_path, csharp_library_path], None)

    project_config_manager.get_project_config.assert_has_calls([mock.call(project_path),
                                                                mock.call(project_path),
                                                                mock.call(python_library_path),
                                                                mock.call(csharp_library_path),
                                                                mock.call(project_path),
                                                                mock.call(python_library_path),
                                                                mock.call(python_library_path),
                                                                mock.call(csharp_library_path),
                                                                mock.call(csharp_library_path)])
    project_config.get.assert_has_calls([mock.call("libraries", []), mock.call("libraries", [])])
    python_library_config.get.assert_has_calls([mock.call("libraries", []),
                                                mock.call("cloud-id", None),
                                                mock.call("libraries", [])])

    api_client.projects.get_all.assert_called_once()
    api_client.projects.add_library.assert_has_calls([mock.call(project_id, python_library_id),
                                                      mock.call(python_library_id, csharp_library_id)])
    api_client.projects.delete_library.assert_not_called()


def test_cloud_push_removes_libraries_in_the_cloud() -> None:
    create_fake_lean_cli_directory()

    lean_config_manager = container.lean_config_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()

    project_path = lean_cli_root_dir / "Python Project"
    library_path = lean_cli_root_dir / "Library/Python Library"

    push_manager = mock.Mock()
    push_manager.push_projects = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    api_client = mock.Mock()
    api_client.projects.add_library = mock.Mock()
    api_client.projects.delete_library = mock.Mock()

    project_id = 1000
    library_id = 1001
    test_project = create_api_project(project_id, project_path.name)
    library = create_api_project(library_id, str(library_path.relative_to(lean_cli_root_dir)))
    test_project.libraries.append(library.projectId)

    cloud_projects = [create_api_project(i, f"Project {i}") for i in range(1, 6)]
    cloud_projects.append(test_project)
    cloud_projects.append(library)

    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)

    container.api_client.override(providers.Object(api_client))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path.name])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once_with([project_path], None)

    api_client.projects.get_all.assert_called_once()
    api_client.projects.add_library.assert_not_called()
    api_client.projects.delete_library.assert_called_once_with(project_id, library_id)


def test_cloud_push_adds_and_removes_libraries_simultaneously() -> None:
    create_fake_lean_cli_directory()

    lean_config_manager = container.lean_config_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()

    project_path = lean_cli_root_dir / "Python Project"

    push_manager = mock.Mock()
    push_manager.push_projects = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    api_client = mock.Mock()
    api_client.projects.add_library = mock.Mock()
    api_client.projects.delete_library = mock.Mock()

    cloud_projects = [create_api_project(i, f"Project {i}") for i in range(1, 6)]
    project_id = 1000
    test_project_library_id = 1001
    test_project = create_api_project(project_id, project_path.name)
    test_project_library = create_api_project(test_project_library_id, "Library/Cloud Library")
    # test_project_library is added in the cloud but not locally, should be removed
    test_project.libraries.append(test_project_library.projectId)
    cloud_projects.append(test_project)
    cloud_projects.append(test_project_library)

    local_library_path = lean_cli_root_dir / "Library/Python Library"
    local_library_id = 1002
    cloud_projects.append(create_api_project(local_library_id, str(local_library_path.relative_to(lean_cli_root_dir))))

    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)

    container.api_client.override(providers.Object(api_client))

    project_config = mock.Mock()
    project_config.file.exists = mock.MagicMock(return_value=True)

    # local_library_path is added locally but not in the cloud, should be added
    project_config.get = mock.MagicMock(return_value=[{
        "name": local_library_path.name,
        "path": str(local_library_path.relative_to(lean_cli_root_dir))
    }])

    library_config = mock.Mock()
    library_config.get = mock.MagicMock(side_effect=[[], str(local_library_id), []])

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(side_effect=[project_config,
                                                                            project_config,
                                                                            library_config,
                                                                            project_config,
                                                                            library_config,
                                                                            library_config])
    container.project_config_manager.override(providers.Object(project_config_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path.name])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once_with([project_path, local_library_path], None)

    project_config_manager.get_project_config.assert_has_calls([mock.call(project_path),
                                                                mock.call(project_path),
                                                                mock.call(local_library_path),
                                                                mock.call(project_path),
                                                                mock.call(local_library_path),
                                                                mock.call(local_library_path)])
    project_config.get.assert_has_calls([mock.call("libraries", []), mock.call("libraries", [])])
    library_config.get.assert_has_calls([mock.call("libraries", []),
                                         mock.call("cloud-id", None),
                                         mock.call("libraries", [])])

    api_client.projects.get_all.assert_called_once()
    api_client.projects.add_library.assert_called_once_with(test_project.projectId, local_library_id)
    api_client.projects.delete_library.assert_called_once_with(test_project.projectId, test_project_library.projectId)
