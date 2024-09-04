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

def test_encrypt_encrypts_file_with_chinese_characters() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("是一的", encoding="utf-8")

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("encrypted", False) == False
    assert project_config.get("encryption-key-path", None) == None

    result = CliRunner().invoke(lean, ["encrypt", "Python Project", "--key", encryption_file_path])

    assert result.exit_code == 0

    source_files = container.project_manager.get_source_files(project_path)
    expected_encrypted_files = _get_expected_encrypted_files_content()
    for file in source_files:
        assert expected_encrypted_files["chinese_" + file.name].strip() == file.read_text().strip()
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
        "chinese_main.py":
            """/hBXLMAwLMr3D0WTwS5lbHxJquOwtubD1rwNFPyrPkaFfn4oJF/MlHR0+ibh0S/HmOfZy3bSaNUNyVlv
GwUc6BkTVduHfl0m0doinxtovFkLMi33PWYwTrdr7tXWoklzq+J+AyjmaYiJsN9GxJvUzM3fsvRR7+5h
6j16o+zI/PHntLsldC2+66e3E1yP+b6uYrOaqubIs6ORGV3G9oViLfKCADiHTRLH+7885cJxN1Is1wOE
5zIIe4DOBnq92XpazPM/1Lk3ECcu/bno2capvjRtqXZiINv7QGGtcHyZ5C4vanfE9KkUbXTaDBtxrxSH
jmI/kNo+2DFM9BQ9YWK8bBYBUEt6cBDnyM6yBC33QCoYVOm37p3lj5mZkeePPSMdLmXfi7tZ7iySuT49
/iWJ88rddbKVKU2qMtGjem5loKTOtKWoqd2R/fpOLAr+rH2D/Zz/hwomD+TdQ3DyWSYES3B9mMhk2Mpk
jtWkTiMMRdOalmC6GyihFbvYVUU19MZr3nTk6aEjRs1lSOZ+HiNV3KcrOY5ZlgLazXWfa9BUPdbXiDNk
m7LoCb2deL+y+cvL92xuu9Vuu3coKPxpVR3wodrJHLvWma22QagNR1wVb3f7agBypJm0/Yjr4+bSfRK0
tNsmCtsMpGmlsFMYae0gl6IVR5VMTohetSf2/Fu2YsSpeBfAp3AN2vM3lfJtrC3WqVhWG+rnNa4ye5N0
OLELdewYwHyeHOq6UQKJ7Bx7andRhogpVp0SeQGtu2y44/PfnaWQXB2z6I4oRipqmwSHLDyvC9sZX4jq
d9zLWdJ3RrpeER0hC9XG1fa3WXG2sVJfjEyd54MFMO5/sgQhU+lbvDlXs2HkIx/bbNUz4yuaE4PD5xcO
9votaJDw3m4zFVBww8m+PO3ddHUUC672lP0jCZcsjYw2WlZNt5bC5DSvvzCVvDzIF5dc3IKKXpeWwadN
fLxzbUCRumfDes0yuw9E+nPKhbLCatXIGlp8c/wpQ+XyWD/SVI/vCJjHAzbYPY7nIVYp0FAnCQ6kpBbI
wb/6GovuiB5bl/zHc5iWw17zy+F//CjAv2RJUgEd4uiQWIOKohSd6yjUWbsvybIyGF+/DLs7F/ZbQqTi
qxP8h0s0CxgTowyBYncfYLOmD2AybNVQUPIE5DNIANKV2xWPTQo8NqZ/oDYFlaobqazmViTfrgM="""
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
bFWAAkX56MyDHwJefC1nkA==""",
        "chinese_research.ipynb":
            """YujNshgrEbvBBeZs6Dod4uQhoSpPAQRn31qHGUcoacZbmpPpm9XoTKOCz9/v3zcFkD/xNP88Ry/Q7Zra
X1k6SjoQsswUB4MM0i4HwieZCug7dKjarlO3OAN/RrMeH2x7DvJQsjDNKMlE1JdLQ2gZXcolLWRoQCsO
TFb/wXx5VhU9XGF756OTKDQmweIkLS8RNHhXgiC0eMwYlPafDz+EA5DDe9p6Vx+xb1wHs7UP+Hhz/ikj
8rL4JWrCRJVbCX0riZE9omwPnAAO2M5kyVNwArMc+H7PIE7zKJqhGwSzt+uXvOCv/3fHazbTEwHErhKK
padpAPsRsJVlgfgm8epD9KywctYvtHpmN1io47yXM4yhWQsLduBqSig4W/rPd54OYPL1af6v+mUhFWdm
XV4mQzO+crVCmEvyKIw85Ai1uXzOs2r10UNS5e+reD+jRz9pg9ZSzUY0wyTfvdL1FG9PJSmsK2uLnC2x
WNfjKW0sbmIOYy2gm8oz0cEOSE303KB//p5Tl57zorzPp2UTNPJZFW9YKD0NGglWKPCtJYDsLNX9gJu5
5Z7+a/S3GeizpV7VbvsoKZw7xYxLbKCfW2eJzgiaDE3XKMyXm6ohS+zZUC+5C1/Fidx2GyzMViDfF+sg
0dmwlxShkESdVHa8AigMkcJ1lIjeTiiBnqU6ujqe9t/HnderOfit2ZLUjEW06ogA32WVzsNXQfpiF1My
fPY92a/uv0Z7hW0FyaJeKC0PhVCfcXWIqjZ3vRx3otDgYGn+fy/Y6dcHZ8gsIMwG0Amd1bxU2hssxXqR
sUiTaZYetwQzoy8qci2hxo7GTdndELWChmZ6IpbdvnLdnMVHfDBE14n7IhrShtk02R9is/hn0BbwK2Hu
UvrYZowKcXKdHcofPR413ak9xlvgNwlyquy4q2NWdYlfxb2vN9QorhhSd5GKyhksbVOTfeklUdRCOza6
neXoiR2e8rv0BNnaBa4vnAhNxB+vp9MeTGFMqfvCRw7HuRT3+wJHwgtP1qjVK7n2jUF1dmAj6Bnxl7ju
Y0AEUsh+ioGjv1Jwn5WKEYuCFNN1YrttCabJP6JI+yjbzf6n6O6Ex10Zmea3rpxLAZ8Jpqm/A0b27XpT
FNEfo86uR5WO5yCmeUAtUCanknoXh41wmA762eJPMXubqlGQGijde3ZSaaSoxHaeCrfxhd63hqxxd8Uf
c7BA4yFmNpn9N9ZRwaSYDqsLmqbdvxhyBJQd3bu1aIMPX2NcxpGV87kjbfNRQCmdvj+H1/n+pFm/4MgU
xEndzUvoSQvRjIeU4eB2R5Um4j/beLMFxd6Is6ku2B3ypYqg9cqcaDuGbXzZ6mxLnpoVCPFCvDsRWJ8c
blGlOV0YfbzUDYlTFWxO/cs3hVOSpjhOVANOAtfQFt9ZLa00B8t1tRCNvjM7EX0nHf41T69c4V7ex+OJ
/5XNCwuWoHZ2GJSni3bxjZ3ZxhGhCkIvxIgGrUTmt1wGOKGKwjl88uD5bDWX4+sjom2oDGqQTvkIlZJn
kKiRBRvuG4VAv0QAv73+QURV0RGxMgedEjIFd8R9Yf2mb7IENzgq2SQSL065qWzoCRTBF+jVOP8fXdzs
KL21W4y756fM3nKMkFGQZbjPeHO5ojDjT/U3mMimgC/3haZy5mmLde9NJFHWM8SuEoA/0bnCgZV++vpZ
kqzmoRw8H4RE+oBT8W+ch6CZvEYYsTuAXIPe1cQBcNxanqk4Uh8gwlEko/zfffPS7r1FR3+pe0AajG+o
wT72mv1dhrRifrr0MVEZe1iRUdPwEjBttJjCr5bnnbmswSKf2fEg0cHRBv25z9t33mj4kth/T2W5zkw3
Zbni33aJFF6uM9VECyU1QlEz5Eu8lhecWs5ZxFtjT73K/5tqmcwNYx7sO1UpT3QPF1DQ7RlP1yTTkTw2
s0ntvYgXO0YOeItR43fpHw=="""
}
