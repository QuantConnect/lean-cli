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


def test_encrypt_encrypts_file_in_case_project_not_in_encrypt_state() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False
    assert project_config.get("encryption-key-path", None) == None

    result = CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    expected_encrypted_files = _get_expected_encrypted_files_content()
    for file in source_files:
        assert expected_encrypted_files[file.name].strip() == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == True
    assert project_config.get("encryption-key-path", None) == str(encryption_file_path)


def test_encrypt_does_not_change_file_in_case_project_already_in_encrypt_state() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path))

    source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in source_files}

    result = CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name] == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == True
    assert project_config.get("encryption-key-path", None) == str(encryption_file_path)


def test_encrypt_uses_key_from_config_file_when_not_provided() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encryption-key-path", str(encryption_file_path))

    result = CliRunner().invoke(lean, ["encrypt", "Python Project"])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    expected_encrypted_files = _get_expected_encrypted_files_content()
    for file in source_files:
        assert expected_encrypted_files[file.name].strip() == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == True
    assert project_config.get("encryption-key-path", None) == str(encryption_file_path)

def test_encrypt_updates_project_config_file() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    result = CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    expected_encrypted_files = _get_expected_encrypted_files_content()
    for file in source_files:
        assert expected_encrypted_files[file.name].strip() == file.read_text()
    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == True
    assert project_config.get("encryption-key-path", None) == str(encryption_file_path)

# def test_encrypt_does_not_update_project_config_file_if_not_all_files_successful() -> None:
#     create_fake_lean_cli_directory()

#     project_path = Path.cwd() / "Python Project"

#     encryption_file_path = project_path / "encryption_x.txt"
#     encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

#     CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

#     project_config = container.project_config_manager.get_project_config(project_path)
#     assert project_config.get("encrypted", False) != False
#     assert project_config.get("encryption-key-path", None) != None

#     # let's corrupt one file
#     source_files = container.project_manager.get_source_files(project_path)
#     source_files[0].write_text("corrupted")
#     file_contents_map = {file.name: file.read_text() for file in source_files}

#     result = CliRunner().invoke(lean, ["decrypt", "Python Project", "--key", encryption_file_path])

#     assert result.exit_code != 0

#     source_files = container.project_manager.get_source_files(project_path)
#     for file in source_files:
#         assert file_contents_map[file.name] == file.read_text()
#     project_config = container.project_config_manager.get_project_config(project_path)
#     assert project_config.get("encrypted", False) != False
#     assert project_config.get("encryption-key-path", None) != None

def test_encrypt_aborts_when_key_is_not_provided_and_not_in_config_file() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    source_files = container.project_manager.get_source_files(project_path)
    file_contents_map = {file.name: file.read_text() for file in source_files}

    result = CliRunner().invoke(lean, ["encrypt", "Python Project"])

    assert result.exit_code != 0

    source_files = container.project_manager.get_source_files(project_path)
    for file in source_files:
        assert file_contents_map[file.name] == file.read_text()

def test_encrypt_aborts_when_provided_key_different_from_key_in_config_file() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path_x = project_path / "encryption_x.txt"
    encryption_file_path_x.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    encryption_file_path_y = project_path / "encryption_y.txt"
    encryption_file_path_y.write_text("Jtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encryption-key-path", str(encryption_file_path_x))

    result = CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path_y])

    assert result.exit_code != 0


def _get_expected_encrypted_files_content() -> dict:
    return {
        "main.py":
                        """UpMdqgoXS1tgqGgy6nKkmp65TT+GqReCQwA+FCyfwGPqW6phpj3l83KaX1Cz0uICPto9QlHVhhbsnRrd
ydsvM2243MT0zUaPSpwD3FoNGPkjcdDCzj1pwJ9Xkgt7vwm9CMAL+NVUI9gd9e+/6zHprEOBwinzufX+
XBlcwHCbePF2mP6d/TWtLVCChiFjipgW0Tpy9UUByQxo9K/j5/PUawTg3gV9xLszlG65aEe2x0upmP9Y
OnZh9Uuyppe8dW4AaZMu64RRmxHWA0m9qH/N7QTJSBchlp/6Y/sWNLqoz6WvqCs8L5iAXVCQ5QYMKV1A
bMmt536DlJ5+4c9vP6omi/wOkoWi30ojQBqGT/n7By5P3bOdCq5Yi7jGRWBRE/IMB26DnRbt9sLPQV2a
TUnW/vjDbT6LUvg2Rgmsroq3fD2etI9GrQN6xp+0jGT7Drib9RwIJl+9dimyjuXwzpanmkdLJZ4d8w9g
cyz/cTa+LaoXbLxDQgvgtDsJYifnDTm7IUJSUov3Uy9Anl5WeVk1XpbFk+9ZHhw2QR8jSJ93eyFDSGyG
xyWltGdAmSBm814G2UJTeMGIBGBqwtel85mQw1sQkXluN86QjZQ7r9f8uBjyHwv7n3mu3ma+IHNfgB4q
f2ZqK6WHGCaYSVUbXLgzD4If/kVPnrwWGrcfJuLis9F8kKFSK5/Hkf7xXNMWAta0WsN5EExga+iVycug
8GAYTJoxaNsqFPssatdmo8OICQ4wIivPW5cCuJltSpBEq9FtVJQRCTKV08EkCw+J1bDSNMJL124UnmiX
9MTdRYiwvN2DQdP+w4pyGdwgffK6qY+1VTZTqcATUE0/cdIM2i/zD9MrVy8KLxGLd+FWZ+bxdCuQF/0F
1oLw/h9MhBZ31fIE3LYMIF+7F/A9wZdw9W6vvj60ITqoWQktXPzCKQIYSRMtZNusCzal5N0v46sKYcta
Z+fCiQL1kY7YjAFmppFUIZHoa47CvW1O4dBlvRhPCT11NeHUF2Ul11dtmY57Y6zgp+cYb7sekwZtRXR5
/chpUYwwJ6bKPQpK5N2wYscRO2yPPqKtjc/tiqKH4MzXzMpr7Vj9GpYn1QaaVCdDPUYz0koHPN7Mhxde
oPBpt0b8sz5XK1vQo8pgzNdhHYHOU5S+8t9odN9hI5BcOxEY+Reub0nD3eR8Upe2Bvnahy6iTek="""
,
"research.ipynb":
                """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
                """
}
