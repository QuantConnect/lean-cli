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
from unittest import mock
from datetime import datetime

from click.testing import CliRunner

from lean.commands import lean
from lean.components.cloud.push_manager import PushManager
from lean.models.api import QCFullFile
from tests.test_helpers import create_fake_lean_cli_directory, create_api_project
from tests.conftest import initialize_container
from lean.container import container
from lean.components.util.encryption_helper import get_project_key_hash

def init_container(**kwargs) -> None:
    organization_manager = mock.Mock()
    organization_manager.get_working_organization_id = mock.MagicMock(return_value="abc")
    organization_manager.try_get_working_organization_id = mock.MagicMock(return_value="abc")

    if "organization_manager_to_use" not in kwargs:
        kwargs["organization_manager_to_use"] = organization_manager

    initialize_container(**kwargs)


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

    push_manager = mock.Mock()
    init_container(api_client_to_use=api_client, push_manager_to_use=push_manager)

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

    push_manager = mock.Mock()
    init_container(api_client_to_use=api_client, push_manager_to_use=push_manager)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    push_manager.push_project.assert_called_once_with(Path.cwd() / "Python Project", None, None)


def test_cloud_push_aborts_when_given_directory_is_not_lean_project() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    init_container(push_manager_to_use=push_manager)

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_aborts_when_given_directory_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    init_container(push_manager_to_use=push_manager)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_updates_lean_config() -> None:

    create_fake_lean_cli_directory()
    project_path = Path.cwd() / "Python Project"
    cloud_project = create_api_project(1, "Python Project")
    api_client = mock.Mock()
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="removed_file.py", content="", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)
    api_client.files.delete = mock.Mock()

    api_client.projects.get_all = mock.MagicMock(return_value=[cloud_project])
    api_client.projects.get = mock.MagicMock(return_value=create_api_project(1, "Python Project"))

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("organization-id", None) == None
    assert cloud_project.organizationId == "123"

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    project_config = container.project_config_manager.get_project_config(project_path)
    assert project_config.get("organization-id", None) == "123"


def test_cloud_push_aborts_when_encrypting_without_key_given() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    init_container(push_manager_to_use=push_manager)

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project", "--encrypt"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()

def test_cloud_push_aborts_when_decrypting_without_key_given() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    init_container(push_manager_to_use=push_manager)

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project", "--decrypt"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_sends_encrypted_files_with_encrypted_flag_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path)
    keys_api_data = {'keys': [{'name': 'test', 'hash': key_hash}]}

    api_client = mock.Mock()
    api_client.encryption_keys.list = mock.MagicMock(return_value=keys_api_data)
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", False)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path, "--encrypt", "--key", encryption_file_path])

    assert result.exit_code == 0
    expected_arguments = {
        "name": "Python Project",
        "description": "",
        "files":[{'name': 'main.py', 'content': 'UpMdqgoXS1tgqGgy6nKkmp65TT+GqReCQwA+FCyfwGPqW6phpj3l83KaX1Cz0uICPto9QlHVhhbsnRrd\nydsvM2243MT0zUaPSpwD3FoNGPkjcdDCzj1pwJ9Xkgt7vwm9CMAL+NVUI9gd9e+/6zHprEOBwinzufX+\nXBlcwHCbePF2mP6d/TWtLVCChiFjipgW0Tpy9UUByQxo9K/j5/PUawTg3gV9xLszlG65aEe2x0upmP9Y\nOnZh9Uuyppe8dW4AaZMu64RRmxHWA0m9qH/N7QTJSBchlp/6Y/sWNLqoz6WvqCs8L5iAXVCQ5QYMKV1A\nbMmt536DlJ5+4c9vP6omi/wOkoWi30ojQBqGT/n7By5P3bOdCq5Yi7jGRWBRE/IMB26DnRbt9sLPQV2a\nTUnW/vjDbT6LUvg2Rgmsroq3fD2etI9GrQN6xp+0jGT7Drib9RwIJl+9dimyjuXwzpanmkdLJZ4d8w9g\ncyz/cTa+LaoXbLxDQgvgtDsJYifnDTm7IUJSUov3Uy9Anl5WeVk1XpbFk+9ZHhw2QR8jSJ93eyFDSGyG\nxyWltGdAmSBm814G2UJTeMGIBGBqwtel85mQw1sQkXluN86QjZQ7r9f8uBjyHwv7n3mu3ma+IHNfgB4q\nf2ZqK6WHGCaYSVUbXLgzD4If/kVPnrwWGrcfJuLis9F8kKFSK5/Hkf7xXNMWAta0WsN5EExga+iVycug\n8GAYTJoxaNsqFPssatdmo8OICQ4wIivPW5cCuJltSpBEq9FtVJQRCTKV08EkCw+J1bDSNMJL124UnmiX\n9MTdRYiwvN2DQdP+w4pyGdwgffK6qY+1VTZTqcATUE0/cdIM2i/zD9MrVy8KLxGLd+FWZ+bxdCuQF/0F\n1oLw/h9MhBZ31fIE3LYMIF+7F/A9wZdw9W6vvj60ITqoWQktXPzCKQIYSRMtZNusCzal5N0v46sKYcta\nZ+fCiQL1kY7YjAFmppFUIZHoa47CvW1O4dBlvRhPCT11NeHUF2Ul11dtmY57Y6zgp+cYb7sekwZtRXR5\n/chpUYwwJ6bKPQpK5N2wYscRO2yPPqKtjc/tiqKH4MzXzMpr7Vj9GpYn1QaaVCdDPUYz0koHPN7Mhxde\noPBpt0b8sz5XK1vQo8pgzNdhHYHOU5S+8t9odN9hI5BcOxEY+Reub0nD3eR8Upe2Bvnahy6iTek='}, {'name': 'research.ipynb', 'content': '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'}],
        "libraries": [],
        "encryption_key": key_hash
    }
    api_client.projects.update.assert_called_once_with(1, **expected_arguments)

def test_cloud_push_aborts_sending_encrypted_files_when_local_file_encrypted_with_key_x_and_given_key_y() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path_x = project_path / "encryption_x.txt"
    encryption_file_path_x.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    encryption_file_path_y = project_path / "encryption_y.txt"
    encryption_file_path_y.write_text("Jtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path_y)
    keys_api_data = {'keys': [{'name': 'test', 'hash': key_hash}]}

    api_client = mock.Mock()
    api_client.encryption_keys.list = mock.MagicMock(return_value=keys_api_data)
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path_x))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path, "--encrypt", "--key", encryption_file_path_y])

    assert result.exit_code == 0
    api_client.projects.update.assert_not_called()

def test_cloud_push_turns_on_encryption_with_encrypted_flag_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path)
    keys_api_data = {'keys': [{'name': 'test', 'hash': key_hash}]}

    api_client = mock.Mock()
    api_client.encryption_keys.list = mock.MagicMock(return_value=keys_api_data)
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", False)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path, "--encrypt", "--key", encryption_file_path])

    assert result.exit_code == 0
    # verify that the 'encryption_key' is being set to turn on the encryption in the cloud.
    expected_arguments = {
        "name": "Python Project",
        "description": "",
        "files":[{'name': 'main.py', 'content': 'UpMdqgoXS1tgqGgy6nKkmp65TT+GqReCQwA+FCyfwGPqW6phpj3l83KaX1Cz0uICPto9QlHVhhbsnRrd\nydsvM2243MT0zUaPSpwD3FoNGPkjcdDCzj1pwJ9Xkgt7vwm9CMAL+NVUI9gd9e+/6zHprEOBwinzufX+\nXBlcwHCbePF2mP6d/TWtLVCChiFjipgW0Tpy9UUByQxo9K/j5/PUawTg3gV9xLszlG65aEe2x0upmP9Y\nOnZh9Uuyppe8dW4AaZMu64RRmxHWA0m9qH/N7QTJSBchlp/6Y/sWNLqoz6WvqCs8L5iAXVCQ5QYMKV1A\nbMmt536DlJ5+4c9vP6omi/wOkoWi30ojQBqGT/n7By5P3bOdCq5Yi7jGRWBRE/IMB26DnRbt9sLPQV2a\nTUnW/vjDbT6LUvg2Rgmsroq3fD2etI9GrQN6xp+0jGT7Drib9RwIJl+9dimyjuXwzpanmkdLJZ4d8w9g\ncyz/cTa+LaoXbLxDQgvgtDsJYifnDTm7IUJSUov3Uy9Anl5WeVk1XpbFk+9ZHhw2QR8jSJ93eyFDSGyG\nxyWltGdAmSBm814G2UJTeMGIBGBqwtel85mQw1sQkXluN86QjZQ7r9f8uBjyHwv7n3mu3ma+IHNfgB4q\nf2ZqK6WHGCaYSVUbXLgzD4If/kVPnrwWGrcfJuLis9F8kKFSK5/Hkf7xXNMWAta0WsN5EExga+iVycug\n8GAYTJoxaNsqFPssatdmo8OICQ4wIivPW5cCuJltSpBEq9FtVJQRCTKV08EkCw+J1bDSNMJL124UnmiX\n9MTdRYiwvN2DQdP+w4pyGdwgffK6qY+1VTZTqcATUE0/cdIM2i/zD9MrVy8KLxGLd+FWZ+bxdCuQF/0F\n1oLw/h9MhBZ31fIE3LYMIF+7F/A9wZdw9W6vvj60ITqoWQktXPzCKQIYSRMtZNusCzal5N0v46sKYcta\nZ+fCiQL1kY7YjAFmppFUIZHoa47CvW1O4dBlvRhPCT11NeHUF2Ul11dtmY57Y6zgp+cYb7sekwZtRXR5\n/chpUYwwJ6bKPQpK5N2wYscRO2yPPqKtjc/tiqKH4MzXzMpr7Vj9GpYn1QaaVCdDPUYz0koHPN7Mhxde\noPBpt0b8sz5XK1vQo8pgzNdhHYHOU5S+8t9odN9hI5BcOxEY+Reub0nD3eR8Upe2Bvnahy6iTek='}, {'name': 'research.ipynb', 'content': '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'}],
        "libraries": [],
        "encryption_key": key_hash
    }
    api_client.projects.update.assert_called_once_with(1, **expected_arguments)

def test_cloud_push_sends_decrypted_files_with_decrypted_flag_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path)
    keys_api_data = {'keys': [{'name': 'test', 'hash': key_hash}]}

    api_client = mock.Mock()
    api_client.encryption_keys.list = mock.MagicMock(return_value=keys_api_data)
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", False)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path, "--decrypt", "--key", encryption_file_path])

    assert result.exit_code == 0
    expeceted_arguments = {
        "name": "Python Project",
        "description": "",
        "files": [{'name': 'main.py', 'content': '# region imports\nfrom AlgorithmImports import *\n# endregion\n\nclass PythonProject(QCAlgorithm):\n\n    def Initialize(self):\n        # Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data\n        self.SetStartDate(2013, 10, 7)  # Set Start Date\n        self.SetEndDate(2013, 10, 11)  # Set End Date\n        self.SetCash(100000)  # Set Strategy Cash\n        self.AddEquity("SPY", Resolution.Minute)\n\n    def OnData(self, data: Slice):\n        """OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.\n            Arguments:\n                data: Slice object keyed by symbol containing the stock data\n        """\n        if not self.Portfolio.Invested:\n            self.SetHoldings("SPY", 1)\n            self.Debug("Purchased Stock")\n'}, {'name': 'research.ipynb', 'content': '{\n    "cells": [\n        {\n            "cell_type": "markdown",\n            "metadata": {},\n            "source": [\n                "![QuantConnect Logo](https://cdn.quantconnect.com/web/i/icon.png)\\n",\n                "<hr>"\n            ]\n        },\n        {\n            "cell_type": "code",\n            "execution_count": null,\n            "metadata": {},\n            "outputs": [],\n            "source": [\n                "# QuantBook Analysis Tool \\n",\n                "# For more information see [https://www.quantconnect.com/docs/v2/our-platform/research/getting-started]\\n",\n                "qb = QuantBook()\\n",\n                "spy = qb.AddEquity(\\"SPY\\")\\n",\n                "# Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data \\n",\n                "qb.SetStartDate(2013, 10, 11)\\n",\n                "history = qb.History(qb.Securities.Keys, 360, Resolution.Daily)\\n",\n                "\\n",\n                "# Indicator Analysis\\n",\n                "bbdf = qb.Indicator(BollingerBands(30, 2), spy.Symbol, 360, Resolution.Daily)\\n",\n                "bbdf.drop(\'standarddeviation\', axis=1).plot()"\n            ]\n        }\n    ],\n    "metadata": {\n        "kernelspec": {\n            "display_name": "Python 3",\n            "language": "python",\n            "name": "python3"\n        }\n    },\n    "nbformat": 4,\n    "nbformat_minor": 2\n}\n'}],
        "libraries": [],
        "encryption_key": ''
    }
    api_client.projects.update.assert_called_once_with(1, **expeceted_arguments)

def test_cloud_push_turns_off_encryption_with_decrypted_flag_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    # Keys API Data
    key_hash = get_project_key_hash(encryption_file_path)
    keys_api_data = {'keys': [{'name': 'test', 'hash': key_hash}]}

    api_client = mock.Mock()
    api_client.encryption_keys.list = mock.MagicMock(return_value=keys_api_data)
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", False)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path, "--decrypt", "--key", encryption_file_path])

    assert result.exit_code == 0
    # verify that the encryption key is set to null to turn off the encryption.
    expeceted_arguments = {
        "name": "Python Project",
        "description": "",
        "files": [{'name': 'main.py', 'content': '# region imports\nfrom AlgorithmImports import *\n# endregion\n\nclass PythonProject(QCAlgorithm):\n\n    def Initialize(self):\n        # Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data\n        self.SetStartDate(2013, 10, 7)  # Set Start Date\n        self.SetEndDate(2013, 10, 11)  # Set End Date\n        self.SetCash(100000)  # Set Strategy Cash\n        self.AddEquity("SPY", Resolution.Minute)\n\n    def OnData(self, data: Slice):\n        """OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.\n            Arguments:\n                data: Slice object keyed by symbol containing the stock data\n        """\n        if not self.Portfolio.Invested:\n            self.SetHoldings("SPY", 1)\n            self.Debug("Purchased Stock")\n'}, {'name': 'research.ipynb', 'content': '{\n    "cells": [\n        {\n            "cell_type": "markdown",\n            "metadata": {},\n            "source": [\n                "![QuantConnect Logo](https://cdn.quantconnect.com/web/i/icon.png)\\n",\n                "<hr>"\n            ]\n        },\n        {\n            "cell_type": "code",\n            "execution_count": null,\n            "metadata": {},\n            "outputs": [],\n            "source": [\n                "# QuantBook Analysis Tool \\n",\n                "# For more information see [https://www.quantconnect.com/docs/v2/our-platform/research/getting-started]\\n",\n                "qb = QuantBook()\\n",\n                "spy = qb.AddEquity(\\"SPY\\")\\n",\n                "# Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data \\n",\n                "qb.SetStartDate(2013, 10, 11)\\n",\n                "history = qb.History(qb.Securities.Keys, 360, Resolution.Daily)\\n",\n                "\\n",\n                "# Indicator Analysis\\n",\n                "bbdf = qb.Indicator(BollingerBands(30, 2), spy.Symbol, 360, Resolution.Daily)\\n",\n                "bbdf.drop(\'standarddeviation\', axis=1).plot()"\n            ]\n        }\n    ],\n    "metadata": {\n        "kernelspec": {\n            "display_name": "Python 3",\n            "language": "python",\n            "name": "python3"\n        }\n    },\n    "nbformat": 4,\n    "nbformat_minor": 2\n}\n'}],
        "libraries": [],
        "encryption_key": ''
    }
    api_client.projects.update.assert_called_once_with(1, **expeceted_arguments)

def test_cloud_push_aborts_when_local_files_in_encrypted_state_and_cloud_project_in_decrypted_state_without_key_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    api_client = mock.Mock()
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path])

    assert result.exit_code == 0
    api_client.projects.update.assert_not_called()

def test_cloud_push_aborts_when_local_files_in_decrypted_state_and_cloud_project_in_encrypted_state_without_key_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")
    key_hash = get_project_key_hash(encryption_file_path)

    api_client = mock.Mock()
    cloud_project = create_api_project(1, "Python Project", encrypted=True, encryptionKey={"name":"test", "id": key_hash})
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path])

    assert result.exit_code == 0
    api_client.projects.update.assert_not_called()

def test_cloud_push_aborts_when_local_files_in_encrypted_state_with_key_x_and_cloud_project_in_encrypted_state_with_key_y() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path_x = project_path / "encryption_x.txt"
    encryption_file_path_x.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    encryption_file_path_y = project_path / "encryption_y.txt"
    encryption_file_path_y.write_text("Jtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    # Keys API Data
    key_hash_y = get_project_key_hash(encryption_file_path_y)

    api_client = mock.Mock()
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project, encrypted=True, encryptionKey={"name":"test", "id": key_hash_y})
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path_x))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path])

    assert result.exit_code == 0
    api_client.projects.update.assert_not_called()
