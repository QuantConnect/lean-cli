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
import os
from pathlib import Path
from unittest import mock

import pytest
from pyfakefs.helpers import reset_ids, set_uid

from lean.container import container
from lean.models.errors import PushFailedError
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory
from tests.conftest import initialize_container


def test_get_cloud_project_pushing_new_project():
    create_fake_lean_cli_directory()

    cloud_project = create_api_project(20, "Python Project")
    cloud_project.description = ""

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]
    api_client.projects.get.return_value = cloud_project

    push_manager = mock.Mock()
    push_manager.push_projects = mock.Mock()
    push_manager.pushed_project_paths = {Path.cwd() / "Python Project": Path.cwd() / "Python Project"}

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(return_value=cloud_project.projectId)
    project_config.is_empty = mock.MagicMock(return_value=False)
    project_config_manager = mock.Mock()
    project_config_manager.try_get_project_config = mock.MagicMock(return_value=None)
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    initialize_container(api_client_to_use=api_client, push_manager_to_use=push_manager,
                         project_config_manager_to_use=project_config_manager)

    cloud_project_manager = container.cloud_project_manager
    created_cloud_project = cloud_project_manager.get_cloud_project("Python Project", push=True)

    assert created_cloud_project == cloud_project

    api_client.projects.get.assert_called_with(cloud_project.projectId, "abc")
    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Python Project"])


def test_get_cloud_project_raises_when_push_of_project_with_cloud_id_fails() -> None:
    create_fake_lean_cli_directory()

    cloud_project = create_api_project(20, "Python Project")

    api_client = mock.Mock()
    api_client.projects.get.return_value = cloud_project

    push_manager = mock.Mock()
    push_manager.push_projects = mock.Mock(return_value=False)

    initialize_container(api_client_to_use=api_client, push_manager_to_use=push_manager)
    container.project_config_manager.get_project_config(Path.cwd() / "Python Project").set("cloud-id", cloud_project.projectId)

    with pytest.raises(PushFailedError):
        container.cloud_project_manager.get_cloud_project("Python Project", push=True)

    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Python Project"])
    api_client.projects.get.assert_not_called()


def test_get_cloud_project_raises_when_push_of_project_given_by_id_fails() -> None:
    create_fake_lean_cli_directory()

    cloud_project = create_api_project(20, "Python Project")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]

    push_manager = mock.Mock()
    push_manager.push_projects = mock.Mock(return_value=False)

    initialize_container(api_client_to_use=api_client, push_manager_to_use=push_manager)
    container.project_config_manager.get_project_config(Path.cwd() / "Python Project").set("cloud-id", cloud_project.projectId)

    with pytest.raises(PushFailedError):
        container.cloud_project_manager.get_cloud_project(str(cloud_project.projectId), push=True)

    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Python Project"])
    api_client.projects.get.assert_not_called()


def test_get_cloud_project_pushes_project_given_by_id_after_its_directory_was_renamed() -> None:
    create_fake_lean_cli_directory()
    (Path.cwd() / "Python Project").rename(Path.cwd() / "Renamed Project")

    cloud_project = create_api_project(20, "Python Project")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]
    api_client.projects.get.return_value = cloud_project

    push_manager = mock.Mock()
    push_manager.push_projects = mock.Mock(return_value=True)

    initialize_container(api_client_to_use=api_client, push_manager_to_use=push_manager)
    container.project_config_manager.get_project_config(Path.cwd() / "Renamed Project").set("cloud-id", cloud_project.projectId)

    assert container.cloud_project_manager.get_cloud_project(str(cloud_project.projectId), push=True) == cloud_project

    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Renamed Project"])
    api_client.projects.get.assert_called_once_with(cloud_project.projectId, "abc")


def test_get_cloud_project_pushes_project_given_by_id_renamed_under_a_workspace_subfolder() -> None:
    create_fake_lean_cli_directory()
    (Path.cwd() / "Sub").mkdir()
    (Path.cwd() / "Python Project").rename(Path.cwd() / "Sub" / "Renamed Project")
    os.chdir(Path.cwd() / "Sub")

    cloud_project = create_api_project(20, "Python Project")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]
    api_client.projects.get.return_value = cloud_project
    api_client.files.get_all.return_value = []

    initialize_container(api_client_to_use=api_client)
    container.project_config_manager.get_project_config(Path.cwd() / "Renamed Project").set("cloud-id", cloud_project.projectId)

    assert container.cloud_project_manager.get_cloud_project(str(cloud_project.projectId), push=True) == cloud_project

    api_client.projects.update.assert_called()
    assert api_client.projects.update.call_args_list[0].kwargs["name"] == "Renamed Project"


@pytest.mark.parametrize("renamed", [True, False])
def test_get_cloud_project_given_by_id_preserves_unrelated_config_it_cannot_parse(renamed: bool) -> None:
    create_fake_lean_cli_directory()
    other_config_path = Path.cwd() / "Other App" / "config.json"
    other_config_content = '{\n// application setting\n"setting": "keep"\n}'
    other_config_path.parent.mkdir()
    other_config_path.write_text(other_config_content)
    if renamed:
        (Path.cwd() / "Python Project").rename(Path.cwd() / "Renamed Project")

    cloud_project = create_api_project(20, "Cloud Only Project")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]
    api_client.projects.get.return_value = cloud_project
    api_client.files.get_all.return_value = []

    initialize_container(api_client_to_use=api_client)
    if renamed:
        container.project_config_manager.get_project_config(Path.cwd() / "Renamed Project").set("cloud-id", cloud_project.projectId)

    assert container.cloud_project_manager.get_cloud_project(str(cloud_project.projectId), push=True) == cloud_project

    assert other_config_path.read_text() == other_config_content
    assert api_client.projects.update.called == renamed


def test_get_cloud_project_given_by_id_skips_directories_it_cannot_list() -> None:
    create_fake_lean_cli_directory()
    unlistable_path = Path.cwd() / "Unlistable"
    unlistable_path.mkdir()

    cloud_project = create_api_project(20, "Cloud Only Project")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]

    initialize_container(api_client_to_use=api_client)

    # Resolve the workspace while its config can still be cached, so only the listing is denied
    container.lean_config_manager.get_cli_root_directory()
    os.chmod(unlistable_path, 0o111)
    set_uid(1000)
    try:
        assert container.cloud_project_manager.get_cloud_project(str(cloud_project.projectId), push=True) == cloud_project
    finally:
        reset_ids()

    api_client.projects.update.assert_not_called()


def test_get_cloud_project_given_by_id_finds_renamed_project_after_an_entry_it_cannot_inspect() -> None:
    create_fake_lean_cli_directory()
    locked_path = Path.cwd() / "Locked"
    (locked_path / "Target").mkdir(parents=True)
    (Path.cwd() / "Link").symlink_to(locked_path / "Target")
    (Path.cwd() / "Sub").mkdir()
    project_path = Path.cwd() / "Sub" / "Renamed Project"
    (Path.cwd() / "Python Project").rename(project_path)

    cloud_project = create_api_project(20, "Python Project")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]
    api_client.projects.get.return_value = cloud_project
    api_client.files.get_all.return_value = []

    initialize_container(api_client_to_use=api_client)
    container.project_config_manager.get_project_config(project_path).set("cloud-id", cloud_project.projectId)

    # Resolve the workspace while its config can still be cached, so only the locked folder is denied
    container.lean_config_manager.get_cli_root_directory()
    os.chmod(locked_path, 0o000)
    set_uid(1000)
    try:
        with pytest.raises(PermissionError):
            (Path.cwd() / "Link").is_dir()
        os.chdir(Path.cwd() / "Sub")
        assert container.cloud_project_manager.get_cloud_project(str(cloud_project.projectId), push=True) == cloud_project
    finally:
        reset_ids()

    api_client.projects.update.assert_called()


@pytest.mark.parametrize("working_directory", ["Python Project", "Sub"])
def test_get_cloud_project_given_by_id_does_not_push_project_outside_the_working_directory(working_directory: str) -> None:
    create_fake_lean_cli_directory()
    (Path.cwd() / "Sub").mkdir()
    os.chdir(Path.cwd() / working_directory)

    cloud_project = create_api_project(20, "Python Project")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]

    initialize_container(api_client_to_use=api_client)
    project_path = container.lean_config_manager.get_cli_root_directory() / "Python Project"
    container.project_config_manager.get_project_config(project_path).set("cloud-id", cloud_project.projectId)

    assert container.cloud_project_manager.get_cloud_project(str(cloud_project.projectId), push=True) == cloud_project

    api_client.projects.update.assert_not_called()
    api_client.projects.create.assert_not_called()


@pytest.mark.parametrize("local_name,cloud_name", [("Unsafe:Project", "Unsafe Project"),
                                                   ("Python Project", "Renamed Project")])
def test_get_cloud_project_follows_project_renamed_by_push(local_name: str, cloud_name: str) -> None:
    create_fake_lean_cli_directory()
    if local_name != "Python Project":
        (Path.cwd() / "Python Project").rename(Path.cwd() / local_name)

    cloud_project = create_api_project(20, cloud_name)

    api_client = mock.Mock()
    api_client.projects.create.return_value = cloud_project
    api_client.projects.get.return_value = cloud_project

    initialize_container(api_client_to_use=api_client)

    returned_cloud_project = container.cloud_project_manager.get_cloud_project(local_name, push=True)

    assert returned_cloud_project == cloud_project
    assert not (Path.cwd() / local_name).exists()
    final_config = container.project_config_manager.get_project_config(Path.cwd() / cloud_name)
    assert final_config.get("cloud-id") == cloud_project.projectId
    api_client.projects.update.assert_called_once()
    api_client.projects.get.assert_called_with(cloud_project.projectId, "abc")


def test_get_cloud_project_leaves_other_project_configs_untouched_when_push_renames_project() -> None:
    create_fake_lean_cli_directory()
    (Path.cwd() / "Python Project").rename(Path.cwd() / "Unsafe:Project")
    other_config_path = Path.cwd() / "Other App" / "config.json"
    other_config_content = '{\n// application setting\n"setting": "keep"\n}'
    other_config_path.parent.mkdir()
    other_config_path.write_text(other_config_content)

    cloud_project = create_api_project(20, "Unsafe Project")

    api_client = mock.Mock()
    api_client.projects.create.return_value = cloud_project
    api_client.projects.get.return_value = cloud_project

    initialize_container(api_client_to_use=api_client)

    assert container.cloud_project_manager.get_cloud_project("Unsafe:Project", push=True) == cloud_project
    assert other_config_path.read_text() == other_config_content


def test_get_cloud_project_returns_pushed_copy_sharing_the_local_id_of_its_original() -> None:
    create_fake_lean_cli_directory()
    original_path = Path.cwd() / "Python Project"
    copy_path = Path.cwd() / "Unsafe:Copy"
    original_config = container.project_config_manager.get_project_config(original_path)
    original_config.set("cloud-id", 10)
    original_config.set("local-id", 123456789)
    copy_path.mkdir()
    for file in original_path.iterdir():
        if file.is_file():
            (copy_path / file.name).write_text(file.read_text())
    container.project_config_manager.get_project_config(copy_path).delete("cloud-id")

    original_cloud_project = create_api_project(10, "Python Project")
    copy_cloud_project = create_api_project(20, "Unsafe Copy")

    api_client = mock.Mock()
    api_client.projects.create.return_value = copy_cloud_project
    api_client.projects.get.side_effect = lambda project_id, _: {10: original_cloud_project,
                                                                 20: copy_cloud_project}[project_id]

    initialize_container(api_client_to_use=api_client)

    assert container.cloud_project_manager.get_cloud_project("Unsafe:Copy", push=True) == copy_cloud_project


def test_get_cloud_project_pushes_read_only_linked_project_without_local_id() -> None:
    create_fake_lean_cli_directory()
    project_path = Path.cwd() / "Python Project"
    config_path = project_path / "config.json"
    config = json.loads(config_path.read_text())
    config.pop("local-id", None)
    config["cloud-id"] = 20
    config_path.write_text(json.dumps(config))

    cloud_project = create_api_project(20, "Python Project")

    api_client = mock.Mock()
    api_client.projects.get.return_value = cloud_project

    initialize_container(api_client_to_use=api_client)

    os.chmod(config_path, 0o444)
    os.chmod(project_path, 0o555)
    set_uid(1000)
    try:
        assert container.cloud_project_manager.get_cloud_project("Python Project", push=True) == cloud_project
    finally:
        reset_ids()

    api_client.projects.update.assert_called_once()
    assert "local-id" not in json.loads(config_path.read_text())
