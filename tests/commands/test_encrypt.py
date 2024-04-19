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
