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
