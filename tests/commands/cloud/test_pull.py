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

def test_cloud_pull_aborts_receiving_encrypted_files_when_cloud_file_encrypted_with_key_x_and_given_key_y() -> None:
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

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", project_path.name, "--encrypt", "--key", encryption_file_path_x])

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

def test_cloud_pull_decrypted_files_when_local_files_in_encrypted_state_and_cloud_project_in_decrypted_state_without_key_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path_x = project_path / "encryption_x.txt"
    encryption_file_path_x.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    api_client = mock.Mock()
    cloud_projects = [create_api_project(1, "Python Project")]
    api_client.projects.get_all.return_value = cloud_projects

    initial_source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in initial_source_files}
    fake_cloud_files = [QCFullFile(name=file.name, content=file.read_text(), modified=datetime.now(), isLibrary=False)
                        for file in initial_source_files]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)
    encrypted_source_files = _get_expected_encrypted_files_content()
    # replace the content of the files with the encrypted content and verify later that they are decrypted.
    for file in initial_source_files:
        file.write_text(encrypted_source_files[file.name])

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
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False

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
mJcVeO1VSlHCA3oNq5kS82YV4Rt0KL0IApPXlV7yAvJW/SbqrOHY57aVV1/y3q/TQJsj92K2E96sISXJ
jJbNRLat9DCo9tu7c+XKQsHlgCu33WfI2H1cUknOasBuyEbrtFSoBAM8f46+thPU7Zx2EZIHkiXFmHPh
FeoKueMiE6DFOeau66LkVJmGy3SIKpCIWQFYHKDNeI0dF4NdxO5W7h6Ro0ew3UWA0TEc14SWDD4oRWPz
L+G9UMzlxZ41lferZKy6JmxFqduTENbT5jo3pnMTZ7OT5sxuVkFKvS5m4OcHt2jNY7HDmx0uy5oMQPwc
KecKbw+0tyS9Bc/b95eofMCXuZ976aV8lGDdeOTnxUNle82b+dWTtAcL2s7AKK6B8nuhZzTPkl6iMBtR
0Nvyjx8YVne5CRIRyFweU88y/d63oefj911nfpBG2q+gUogNZD8rCRbWCYtYXCUytz/tHDQf0ZWAqe40
Y+Y4fbVfgyQ7exfsmNB31DFUHcoFKjS6o6fU1Rel/KAVkjbcG8THKmDyv07Rtez8qRSND+vNTUJAjmxh
r8KFaksyX252Mfoy8+9mr2TeQeWl8acFGwaQTuyxSYmvOd84SUGsTP8pHtQ9I+phiHXAOfHaQ36PSWvo
q4TSr2yY1zRZtLXTMLbEfZCQz7F6DqmOxCW1JMkLvC9EfqHcad1KfhONpGWdiAeZEe8n3NoN5p8L/nn5
WZV968oSK5HC5WJsK2+w8XamQhBi1YxuIxFN2rZ53MzEzGJZx6QOKQiOEKFS3oheygBYBSFxuovzFJdZ
iaL5FDXrD9WwUrqgy4NQYKXvNcme+qkYp6z8rGMRaLfPzBwl1gjpyuE0UIwCTGPZ/qL0xqKeyrBLHCQV
Fh/ZJnVdf41A5snQgeotDAFrohOnkafbXBg4pqd5ZQ+G5hSg+BTXqIaydbYR4RwBN/RgHb9jfKDZFd1i
4T/vRU2aSdisuNMdXyuF4OH7ZgBdUYaNtfxmuJlmS4tYsom5xJfxrEEGG203gq0ME5eZCmu4JlLbEo1w
L4u74Hsr4mWkJKbMJMcwW8ByRuy/VJiWW8JKIcoB0yHlwLJ/YoqMDF0BPG5i2EF0DXu1USNC/vE="""
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
NWh9y3qZ6aMOMq3dDAr4wGBkkGQsirasCEt3YEa9rG5CDH8JYApCeaDioLeCA5k0ub2OkbfEN0IlXj/8
Y2R+plJgG1DT+YWebyvY/54Ct0lsZ2Q3mKOci9cesrdoLwakcmbMcBw/+0SFXZTXKN29xMTc9aY0BLdL
LakUDL2drQhlxQZUJ7sDKtwL1yCkcagSjXBFkptNifbT6dM64klo/mr1G8NJwWwvKBHGeEoEiDByOk+7
7dEJDe6ogFWh0iucrmOr8c1cKeEPp5Z5MAGkDLNQWo+tosuspqJdEIReAgFVMg9U+ebp8CaUUFaj24T2
fa/X8D9Noq3k2riBIMTtJYMxFz4iFrFfXV7NGJfI4F5+wlEZwOLypuLSk6g9upIJL0JmaHPkapeFBrc5
JxRPUfKO/vUl7MFIcGGOYsPRTdziC4Xql13DdoRxWYxuXgZT3d41kEsOsJYUg9d0djE8+1jLDTWQ3WGJ
Ph2j6d2HCeg2i37wsGSfEi/lxbEca3qYSNQFGe20jp+XKz5SWddK1YU+eUDI661LYiqumCQrpVp1WJT5
IZBSK+VDp1bDEIZmNDOLx7hQ1o2ZLjubIDKA0PKDTUP/HobY/QrTM/QRYXyVFQnzSnYH02SaWYa5gKrV
kxGUD6HHzZ8Cq20kX4rPNWpqna4u9pEdfwuWWPzFrV7R5lNoogqPPVu3BkZ48vdxWp1Y0wXlb4crQqzf
8qj0zZeZiEf6wPA805MCoPb7M/SUpgTV1+eWePFpbBTQk9JI9utcr1nojf/eAfNEw6T4zzpg/9h8gGSh
olU0isNw6Xn7NgOkwq9RaFbHkY/1DM6eR1tWd6qo2IGjh/M0s2C1f16rkaOLdZ2x7v5g1XbnvQTTJFUD
HrFPt9ElvzsATZvrloOCorTqbWc5BYmXb+u4MZ4vLtnU2wq/j5B+DvSswQkXsvtlGDsNPwLyi4dZuIVV
Oae0ese2fAU8lmosUY95ghYxEOGrMHg5ZPklje/afjpxwKAAgTfWqozYPdpNL+MJEqrVA9YRq5wSvjuX
UGw0ehtO8qY5FmPGcUlkBGuqmd7r6aLE4mosoZrc/UyZb+clWNYJITRLFJbQpWm3EU/Xrt5UM8uWwEdV
bFWAAkX56MyDHwJefC1nkA=="""
}
