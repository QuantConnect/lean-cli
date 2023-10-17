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
from click.testing import CliRunner

from lean.commands import lean
from tests.test_helpers import create_fake_lean_cli_directory
from lean.container import container


def test_decrypt_decrypts_file_in_case_project_not_in_decrypt_state() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in source_files}

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    result = CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) != False
    assert project_config.get("encryption-key-path", None) != None
    for file in source_files:
        assert file_contents_map[file.name] != file.read_text()

    result = CliRunner().invoke(lean, ["decrypt", "Python Project", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name] == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False
    assert project_config.get("encryption-key-path", None) == None


def test_decrypt_does_not_change_file_in_case_project_already_in_decrypt_state() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False
    assert project_config.get("encryption-key-path", None) == None

    source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in source_files}
    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    result = CliRunner().invoke(lean, ["decrypt", "Python Project", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name] == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False
    assert project_config.get("encryption-key-path", None) == None


def test_decrypt_uses_key_from_config_file_when_not_provided() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in source_files}

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) != False
    assert project_config.get("encryption-key-path", None) != None
    for file in source_files:
            assert file_contents_map[file.name] != file.read_text()

    result = CliRunner().invoke(lean, ["decrypt", "Python Project"])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name] == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False
    assert project_config.get("encryption-key-path", None) == None

def test_decrypt_updates_project_config_file() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in source_files}

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) != False
    assert project_config.get("encryption-key-path", None) != None
    for file in source_files:
            assert file_contents_map[file.name] != file.read_text()

    result = CliRunner().invoke(lean, ["decrypt", "Python Project", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name] == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False
    assert project_config.get("encryption-key-path", None) == None

def test_decrypt_does_not_update_project_config_file_if_not_all_files_successful() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) != False
    assert project_config.get("encryption-key-path", None) != None

    # let's corrupt one file
    source_files = container.project_manager.get_source_files(project_path)
    source_files[0].write_text("corrupted")
    file_contents_map = {file.name: file.read_text() for file in source_files}

    result = CliRunner().invoke(lean, ["decrypt", "Python Project", "--key", encryption_file_path])

    assert result.exit_code != 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name] == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) != False
    assert project_config.get("encryption-key-path", None) != None

def test_decrypt_aborts_when_key_is_not_provided_and_not_in_config_file() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    project_config = container.project_config_manager.get_project_config(project_path)
    source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in source_files}
    assert project_config.get("encrypted", False) == False
    project_config.set("encrypted", True)

    result = CliRunner().invoke(lean, ["decrypt", "Python Project"])

    assert result.exit_code != 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name] == file.read_text()

def test_decrypt_aborts_when_provided_key_different_from_key_in_config_file() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path_x = project_path / "encryption_x.txt"
    encryption_file_path_x.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    encryption_file_path_y = project_path / "encryption_y.txt"
    encryption_file_path_y.write_text("Jtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path_x])

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) != False
    assert project_config.get("encryption-key-path", None) != None

    result = CliRunner().invoke(lean, ["decrypt", "Python Project", "--key", encryption_file_path_y])

    assert result.exit_code != 0
