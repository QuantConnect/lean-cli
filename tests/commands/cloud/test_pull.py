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

from unittest import mock
from pathlib import Path
from datetime import datetime
from click.testing import CliRunner
from lean.models.api import QCFullFile
from lean.commands import lean
from lean.container import container
from tests.conftest import initialize_container
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory
from lean.components.util.encryption_helper import get_project_key_hash

def init_container(**kwargs) -> None:
    organization_manager = mock.Mock()
    organization_manager.get_working_organization_id = mock.MagicMock(return_value="abc")
    organization_manager.try_get_working_organization_id = mock.MagicMock(return_value="abc")

    if "organization_manager_to_use" not in kwargs:
        kwargs["organization_manager_to_use"] = organization_manager

    initialize_container(**kwargs)

def test_cloud_pull_pulls_all_non_bootcamp_projects_when_no_options_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client = api_client

    pull_manager = mock.Mock()
    container.pull_manager = pull_manager

    result = CliRunner().invoke(lean, ["cloud", "pull"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with(cloud_projects[:3], cloud_projects, None, None)


def test_cloud_pull_pulls_all_projects_when_pull_bootcamp_option_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client = api_client

    pull_manager = mock.Mock()
    container.pull_manager = pull_manager

    result = CliRunner().invoke(lean, ["cloud", "pull", "--pull-bootcamp"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with(cloud_projects, cloud_projects, None, None)


def test_cloud_pull_pulls_project_by_id() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]
    project_to_pull = cloud_projects[0]

    api_client = mock.Mock()
    api_client.projects.get.return_value = project_to_pull
    container.api_client = api_client

    pull_manager = mock.Mock()
    container.pull_manager = pull_manager

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_to_pull.projectId])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with([project_to_pull], None, None, None)


def test_cloud_pull_pulls_project_by_name() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client = api_client

    pull_manager = mock.Mock()
    container.pull_manager = pull_manager

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "Project 1"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with([cloud_projects[0]], cloud_projects, None, None)


def test_cloud_pull_aborts_when_project_input_matches_no_cloud_projects() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client = api_client

    pull_manager = mock.Mock()
    container.pull_manager = pull_manager

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "Project 4"])

    assert result.exit_code != 0

    pull_manager.pull_projects.assert_not_called()

def test_cloud_pull_aborts_when_encrypting_without_key_given() -> None:
    create_fake_lean_cli_directory()

    pull_manager = mock.Mock()
    container.pull_manager = pull_manager

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "Empty Project", "--encrypt"])

    assert result.exit_code != 0

    pull_manager.pull_projects.assert_not_called()

def test_cloud_pull_aborts_when_decrypting_without_key_given() -> None:
    create_fake_lean_cli_directory()

    pull_manager = mock.Mock()
    container.pull_manager = pull_manager

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "Empty Project", "--decrypt"])

    assert result.exit_code != 0

    pull_manager.pull_projects.assert_not_called()


def test_cloud_pull_receives_encrypted_files_with_encrypted_flag_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    cloud_projects = [create_api_project(1, "Python Project")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects

    initial_source_files = container.project_manager.get_source_files(project_path)
    fake_cloud_files = [QCFullFile(name=file.name, content=file.read_text(), modified=datetime.now(), isLibrary=False)
                        for file in initial_source_files]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path))
    project_config.set("cloud-id", 1)

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name, "--encrypt", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    expected_encrypted_files = _get_expected_encrypted_files_content()
    for file in source_files:
        assert expected_encrypted_files[file.name].strip() == file.read_text().strip()

def test_cloud_pull_aborts_receiving_encrypted_files_when_local_file_encrypted_with_key_x_and_given_key_y() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path_x = project_path / "encryption_x.txt"
    encryption_file_path_x.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    encryption_file_path_y = project_path / "encryption_y.txt"
    encryption_file_path_y.write_text("Jtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    key_hash_y = get_project_key_hash(encryption_file_path_y)

    api_client = mock.Mock()
    cloud_project = create_api_project(1, "Python Project", encrypted=True, encryptionKey={"name":"test", "id": key_hash_y})
    cloud_projects = [cloud_project]
    api_client.projects.get_all.return_value = cloud_projects
    api_client.projects.get.return_value = cloud_project

    initial_source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in initial_source_files}
    fake_cloud_files = [QCFullFile(name=file.name, content=file.read_text(), modified=datetime.now(), isLibrary=False)
                        for file in initial_source_files]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path_x))
    project_config.set("cloud-id", 1)

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name, "--encrypt", "--key", encryption_file_path_y])

    assert result.exit_code == 0
    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name].strip() == file.read_text().strip()

def test_cloud_pull_turns_on_encryption_with_encrypted_flag_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path)
    cloud_project = create_api_project(1, "Python Project", encrypted=True, encryptionKey={"name":"test", "id": key_hash})
    cloud_projects = [cloud_project]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    api_client.projects.get.return_value = cloud_project

    initial_source_files = container.project_manager.get_source_files(project_path)
    fake_cloud_files = [QCFullFile(name=file.name, content=file.read_text(), modified=datetime.now(), isLibrary=False)
                        for file in initial_source_files]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)
    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("cloud-id", 1)
    assert project_config.get("encrypted", False) == False
    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name, "--encrypt", "--key", encryption_file_path])

    assert result.exit_code == 0

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == True

def test_cloud_pull_receives_decrypted_files_with_decrypted_flag_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path)

    cloud_project = create_api_project(1, "Python Project", encrypted=True, encryptionKey={"name":"test", "id": key_hash})
    cloud_projects = [cloud_project]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    api_client.projects.get.return_value = cloud_project

    encrypted_source_files = _get_expected_encrypted_files_content()
    initial_source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in initial_source_files}
    # replace the content of the files with the encrypted content and verify later that they are decrypted.
    for file in initial_source_files:
        file.write_text(encrypted_source_files[file.name])
    fake_cloud_files = [QCFullFile(name=name, content=content, modified=datetime.now(), isLibrary=False)
                        for name, content in encrypted_source_files.items()]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)
    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("cloud-id", 1)
    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name, "--decrypt", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name].strip() == file.read_text().strip()

def test_cloud_pull_turns_off_encryption_with_decrypted_flag_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path)

    cloud_project = create_api_project(1, "Python Project", encrypted=True, encryptionKey={"name":"test", "id": key_hash})
    cloud_projects = [cloud_project]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    api_client.projects.get.return_value = cloud_project

    encrypted_source_files = _get_expected_encrypted_files_content()
    fake_cloud_files = [QCFullFile(name=name, content=content, modified=datetime.now(), isLibrary=False)
                        for name, content in encrypted_source_files.items()]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)
    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path))
    project_config.set("cloud-id", 1)

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name, "--decrypt", "--key", encryption_file_path])

    assert result.exit_code == 0

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False

def test_cloud_pull_aborts_when_local_files_in_encrypted_state_and_cloud_project_in_decrypted_state_without_key_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path_x = project_path / "encryption_x.txt"
    encryption_file_path_x.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    encryption_file_path_y = project_path / "encryption_y.txt"
    encryption_file_path_y.write_text("Jtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    api_client = mock.Mock()
    cloud_projects = [create_api_project(1, "Python Project")]
    api_client.projects.get_all.return_value = cloud_projects

    initial_source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in initial_source_files}
    fake_cloud_files = [QCFullFile(name=file.name, content=file.read_text(), modified=datetime.now(), isLibrary=False)
                        for file in initial_source_files]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path_x))
    project_config.set("cloud-id", 1)

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name])

    assert result.exit_code == 0
    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name].strip() == file.read_text().strip()

def test_cloud_pull_encrypts_when_local_files_in_decrypted_state_and_cloud_project_in_encrypted_state_without_key_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path)

    cloud_project = create_api_project(1, "Python Project", encrypted=True, encryptionKey={"name":"test", "id": key_hash})
    cloud_projects = [cloud_project]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    api_client.projects.get.return_value = cloud_project

    encrypted_source_files = _get_expected_encrypted_files_content()
    fake_cloud_files = [QCFullFile(name=name, content=content, modified=datetime.now(), isLibrary=False)
                        for name, content in encrypted_source_files.items()]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)
    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("cloud-id", 1)
    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    expected_encrypted_files = _get_expected_encrypted_files_content()
    for file in source_files:
        assert expected_encrypted_files[file.name].strip() == file.read_text().strip()

def test_cloud_pull_aborts_when_local_files_in_encrypted_state_with_key_x_and_cloud_project_in_encrypted_state_with_key_y() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path_x = project_path / "encryption_x.txt"
    encryption_file_path_x.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    encryption_file_path_y = project_path / "encryption_y.txt"
    encryption_file_path_y.write_text("Jtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    # Keys API Data
    key_hash_y = get_project_key_hash(encryption_file_path_y)

    api_client = mock.Mock()
    cloud_project = create_api_project(1, "Python Project", encrypted=True, encryptionKey={"name":"test", "id": key_hash_y})
    cloud_projects = [cloud_project]
    api_client.projects.get_all.return_value = cloud_projects
    api_client.projects.get.return_value = cloud_project

    initial_source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in initial_source_files}
    fake_cloud_files = [QCFullFile(name=file.name, content=file.read_text(), modified=datetime.now(), isLibrary=False)
                        for file in initial_source_files]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path_x))
    project_config.set("cloud-id", 1)
    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name])

    assert result.exit_code == 0
    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name].strip() == file.read_text().strip()


def _get_expected_encrypted_files_content() -> dict:
    return {
        "main.py":
                """UpMdqgoXS1tgqGgy6nKkmlxrOV7ikoc5oJAmS+pcMcmD0qsfJq5GE/yvdg9mucXrhfgLjD7of3YalHYC
mJcVeO1VSlHCA3oNq5kS82YV4Rt0KL0IApPXlV7yAvJW/SbqcziwPXb/OSmHroQfaD9IJWJdNXrcjfs1
CAXq8mV0BX0OipDTnQL2EfHCDNn3PL7lJPg0lYOKjSuMf6QgvFWElT6Kw0UDiLtKlU6jJwsKxeJDDRAw
KkMJVrrIsxk5g92ERCquoTmYHVm1lf0xdsM+vTqSRxwucEfaoi7DgA9SkJKgaVoDgx90ScqssPzdlsgJ
zIUdPbHO1GN1D5ZfHXU+7Sww4pHDh6QTyLYnuOHnPQ8IuXYDWQPdw9QaHrbeuWqqwyFl859Tra6RZFlD
136K2CZ6PcClbGeeGO2NmGPRFuwHH5B5aSfUs8Y3OMdYnZylXtuWAMPU6xEZIWfGHIOZlQZ7s06rvfYT
CfMHdkFCRi9QnI1vRbqO4yhBDB/BbAG9W7wt/FX1f+1hHk3xpaP+MLufoN48xXSxudIV975Jxdoic8YK
P/6UZ5FWDVTZDRzJ7e9hiS5LOr410G8PqDOr0JuNap3t2FvGLuuR1CFfXsHm2QcsaJgiODzAa/xSW2vq
ffQPkZxz3bhGpuJXoWe18B92m0/Scih5J224QMXoZJYs6UYEl6eQX67mlGSSntotykByWB7upnPFDPSU
l9if+gA+GrW3hyVhDSY/5W9mUA6mw7lelE0b+0cAfuEczDXInQeMbQjAtEOJufIQl7NSZVzc4BWOFoXS
VK3OnsQnbg2f9WN7mQ4UE2xVoVAOudDPSXh21HjhUa9DbqrFy4FQN66G8LgbF6Sw58d+HfCIPOVoNl1f
mMJBPythF0UjBYwle+2EpDC/9WdsVrm02OCEehbs4gfG0vOTtmwMY0Y4Urpxs01ATOfoZEg5gRPMFRD7
zFhH4MGKrPdBA3NXnvRozJsdHRBEVPhmuhtideHMKs68o8BwDLJ8oY6dyyxpjlFhGlHELGDTo7ljCRtR
6d5M+DpJn9vEZ9xWFe60vkgIq3dpn3SwPnrrsd2Ee5TwagDF2Bj8EhMVhshlxjrNR9NNguYgZVFUAJEM
InB4pibT1Q0FLnwFOp84t8offZ5w+hmGm7Jggs99qmx2Tmu4u4067A=="""
,
"research.ipynb":
                """NIiAgzU8gzaJ3YEIWysBh0e0xxm9rpAWDE4Pir/wzKtla/wcbs98GU5cdOxgd7Gjlcu0zNbFzE5x8Eyx
qSuh3cQU17xQSisPxvjfDD/h2z9AnFT1jD1Vhc+Nn5ngwpgCA6P5fHT4VhPgaKDp7r9zc8pAURcSd04M
2dmHtGs89it3QFrYNgYAvN4kIYVZuROhnUSiYN+y7kzWzLKLIK3a+y6R4ibr9ju5S0DCtIS87MwrHFbi
NmS0mqnlYmBqLPVijrgAJYu4YmqrOb+LxwQSUXL80UsgddUFtgKWDKGyTVFs0o92/x9OT2XTCcMOhhQg
X/6h5c99rP5W3GqkcDaaiueShSD43u3LXnijK6yugUqALcMIBLxF4Iczq3xLov9MfrdgDUaxFEOu0dDK
JpecJeSx9TxVUxzcWvn3alUycScBRV1w8VH0Wa4Lf9vc1YIOe9ITy/hLW2+QEBAHxrhYd7vq1MVVDdRI
lbXtLVMOVI9YYBNEunf3drQm6fCnKv+arnt/rYSIQDvhrlqem6qKS3JE4V8gVzXQDefTewx3/hppDOxL
+ccikaUcVkIAULF1Jwp9qxCpCsiz5vLXynD47pf3mhS2FC6Dd1g30xXUVNeTmpRE7TfS/gHzkyDrtTvC
LBvBnkImsJQjDCJl/NzLlFRh4wiY4SL/bTdxL2YZJebJ1zdw3PXQhvWvgztG0wmIRE/U+1xv95gc5w5x
7N2WT7F9KVHI6NrtrcU6c5hWo4q/QEBxb5ETSyNpgsVHvKxKblPGslki/aH6WOexu7tSzbuA9rSwVgiS
NWh9y3qZ6aMOMq3dDAr4wGBkkGQsirasCEt3YEa9rG5CDH8JYApCeZk39zt+oqjQ4DcYprgW/q87fFRB
thxY4cM3BGG/IIpX9oAxvFNe7PSXIx3BBkyhqiJqJRhS3YfvasBWFnJd11h9JXVsKJudVBoJvwrzxldU
Td2mSr1d//xkIe6TeqPK3ivofMoCNoDYyO57juki8ban9Z8q0lpgShWBM8zUPNnezctwJZIp6aVaVdfC
nZtG49f06w1IRC0dOj6yM+adiEPx/vKxrCn1sqd0eoAeKIs5iEm398YJlt9G0eubSSpoDC6iH1GjwH8A
NFNRoKncB4c3ocmajgNda4o32UfpwvNr+fKLmpP+57dulpA09i/FqwF2L8dDNm4JSTjfNdeooM9TIDsG
b3CIItqmNnve8fryEykjE8WgJaP70rnsXRY6WHLivy7OTNMKG8Ij9MOyx44Wq3TWY/omRDjYgfCO4QRZ
vTtlnIMp8VtLlBgxRc6TBPZutYZXDJyY4N4n2Jpspl3KUbe3iHNm6nwl0SCwrIl3aYbCs55BP/LOGXLx
dNIZzkxJhnfLtomrxO4QgcUnjNEWYJ1GvRAplTa99RFFYXOuMQID4+UH+6RM2e6cqBafv+2+lpetfbBM
gMOA+qNdar9Y+b+vLuSz2ak0MCn3h8cAAlXgKNpo4shbgn+R4TViLGfhUZbcSG9VZ0UEBYyg5nxXggqh
fPkc80yGC7lwo0XmrQrp62IaQy3iB2MYWB29KCX9MdghcobfhmW3BEtYqDRLE61/MWYi9scowMkf0TxT
DyMRNS9qVwJ+2gS44xD+lQmQuE1aM+rBmRkVKWA+fB5HzZe6yyN8GkM4D23hcw+DBs9opXvq6QyGd8Le
KqLYkbp7Be44+d6mie1aGp0hRUjF9LzNapPdnYusx4QwoIlt0wYTr1waqAYMG73PhDI36B6oa4tOwuSj
86Wje1jEfUK01LVuVYloclnG3fTQxQlUcrRyQNCbrg0M5elYWbjYybx51/gb//9McGYXW0SWltNlvLvL
SUroK4+Yhqfk5MVeascvM94fFBfieT3erU8D+iCiaVvZGcuE5mE0bLBquXpMuO4fQ06XVI/NzlhVILrV
yXa/cl9WaYDFPqM+eFVJfg=="""
}
