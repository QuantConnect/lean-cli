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

    push_manager.push_project.assert_called_once_with(Path.cwd() / "Python Project", None, None, False)


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


def test_cloud_push_sends_encrypted_files_and_turns_on_encryption_with_encrypted_flag_given() -> None:
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
    expected_encrypted_files = _get_expected_encrypted_files_content()
    # verify that the 'encryption_key' is being set to turn on the encryption in the cloud.
    expected_arguments = {
        "name": "Python Project",
        "description": "",
        "files":[{'name': name, 'content': content} for name, content in expected_encrypted_files.items()],
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

def test_cloud_push_sends_decrypted_files_and_turns_off_encryption_with_decrypted_flag_given() -> None:
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
    # verify that the encryption key is set to empty string to turn off the encryption.
    expected_arguments = {
        "name": "Python Project",
        "description": "",
        "files": [{'name': 'main.py', 'content': '# region imports\nfrom AlgorithmImports import *\n# endregion\n\nclass PythonProject(QCAlgorithm):\n\n    def initialize(self):\n        # Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data\n        self.set_start_date(2013, 10, 7)  # Set Start Date\n        self.set_end_date(2013, 10, 11)  # Set End Date\n        self.set_cash(100000)  # Set Strategy Cash\n        self.add_equity("SPY", Resolution.MINUTE)\n\n    def on_data(self, data: Slice):\n        """on_data event is the primary entry point for your algorithm. Each new data point will be pumped in here.\n            Arguments:\n                data: Slice object keyed by symbol containing the stock data\n        """\n        if not self.portfolio.invested:\n            self.set_holdings("SPY", 1)\n            self.debug("Purchased Stock")\n'}, {'name': 'research.ipynb', 'content': '{\n    "cells": [\n        {\n            "cell_type": "markdown",\n            "metadata": {},\n            "source": [\n                "![QuantConnect Logo](https://cdn.quantconnect.com/web/i/icon.png)\\n",\n                "<hr>"\n            ]\n        },\n        {\n            "cell_type": "code",\n            "execution_count": null,\n            "metadata": {},\n            "outputs": [],\n            "source": [\n                "# QuantBook Analysis Tool \\n",\n                "# For more information see [https://www.quantconnect.com/docs/v2/our-platform/research/getting-started]\\n",\n                "qb = QuantBook()\\n",\n                "spy = qb.add_equity(\\"SPY\\")\\n",\n                "# Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data \\n",\n                "qb.set_start_date(2013, 10, 11)\\n",\n                "history = qb.history(qb.securities.keys(), 360, Resolution.DAILY)\\n",\n                "\\n",\n                "# Indicator Analysis\\n",\n                "bbdf = qb.indicator(BollingerBands(30, 2), spy.symbol, 360, Resolution.DAILY)\\n",\n                "bbdf.drop(\'standarddeviation\', axis=1).plot()"\n            ]\n        }\n    ],\n    "metadata": {\n        "kernelspec": {\n            "display_name": "Python 3",\n            "language": "python",\n            "name": "python3"\n        }\n    },\n    "nbformat": 4,\n    "nbformat_minor": 2\n}\n'}],
        "libraries": [],
        "encryption_key": ''
    }
    api_client.projects.update.assert_called_once_with(1, **expected_arguments)

def test_cloud_push_sends_decrypted_files_when_project_in_encrypted_state_with_decrypted_flag_given() -> None:
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
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path))
    # update the project with encrypted files so that it's in encrypted state
    expected_encrypted_files = _get_expected_encrypted_files_content()
    source_files = container.project_manager.get_source_files(project_path)
    for source_file in source_files:
        source_file.write_text(expected_encrypted_files[source_file.name])

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path, "--decrypt", "--key", encryption_file_path])

    assert result.exit_code == 0
    # verify that the encryption key is set to empty string to turn off the encryption.
    expected_arguments = {
        "name": "Python Project",
        "description": "",
        "files": [{'name': 'main.py', 'content': '# region imports\nfrom AlgorithmImports import *\n# endregion\n\nclass PythonProject(QCAlgorithm):\n\n    def initialize(self):\n        # Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data\n        self.set_start_date(2013, 10, 7)  # Set Start Date\n        self.set_end_date(2013, 10, 11)  # Set End Date\n        self.set_cash(100000)  # Set Strategy Cash\n        self.add_equity("SPY", Resolution.MINUTE)\n\n    def on_data(self, data: Slice):\n        """on_data event is the primary entry point for your algorithm. Each new data point will be pumped in here.\n            Arguments:\n                data: Slice object keyed by symbol containing the stock data\n        """\n        if not self.portfolio.invested:\n            self.set_holdings("SPY", 1)\n            self.debug("Purchased Stock")\n'}, {'name': 'research.ipynb', 'content': '{\n    "cells": [\n        {\n            "cell_type": "markdown",\n            "metadata": {},\n            "source": [\n                "![QuantConnect Logo](https://cdn.quantconnect.com/web/i/icon.png)\\n",\n                "<hr>"\n            ]\n        },\n        {\n            "cell_type": "code",\n            "execution_count": null,\n            "metadata": {},\n            "outputs": [],\n            "source": [\n                "# QuantBook Analysis Tool \\n",\n                "# For more information see [https://www.quantconnect.com/docs/v2/our-platform/research/getting-started]\\n",\n                "qb = QuantBook()\\n",\n                "spy = qb.add_equity(\\"SPY\\")\\n",\n                "# Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data \\n",\n                "qb.set_start_date(2013, 10, 11)\\n",\n                "history = qb.history(qb.securities.keys(), 360, Resolution.DAILY)\\n",\n                "\\n",\n                "# Indicator Analysis\\n",\n                "bbdf = qb.indicator(BollingerBands(30, 2), spy.symbol, 360, Resolution.DAILY)\\n",\n                "bbdf.drop(\'standarddeviation\', axis=1).plot()"\n            ]\n        }\n    ],\n    "metadata": {\n        "kernelspec": {\n            "display_name": "Python 3",\n            "language": "python",\n            "name": "python3"\n        }\n    },\n    "nbformat": 4,\n    "nbformat_minor": 2\n}\n'}],
        "libraries": [],
        "encryption_key": ''
    }
    api_client.projects.update.assert_called_once_with(1, **expected_arguments)

def test_cloud_push_encrypts_when_local_files_in_encrypted_state_and_cloud_project_in_decrypted_state_without_key_given() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"

    encryption_file_path = project_path / "encryption_x.txt"
    encryption_file_path.write_text("KtSwJtq5a4uuQmxbPqcCP3d8yMRz5TZxDBAKy7kGwPcvcvsNBdCprGYwSBN8ntJa5JNNYHTB2GrBpAbkA38kCdnceegffZH7")

    key_hash = get_project_key_hash(encryption_file_path)
    keys_api_data = {'keys': [{'name': 'test', 'hash': key_hash}]}

    api_client = mock.Mock()
    api_client.encryption_keys.list = mock.MagicMock(return_value=keys_api_data)
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="file.py", content="testing", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)
    # update the project with encrypted files so that it's in encrypted state
    expected_encrypted_files = _get_expected_encrypted_files_content()
    source_files = container.project_manager.get_source_files(project_path)
    for source_file in source_files:
        source_file.write_text(expected_encrypted_files[source_file.name])

    init_container(api_client_to_use=api_client)

    project_config = container.project_config_manager.get_project_config(project_path)
    project_config.set("encrypted", True)
    project_config.set("encryption-key-path", str(encryption_file_path))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path])

    assert result.exit_code == 0
    source_files = container.project_manager.get_source_files(project_path)
    expected_encrypted_files = _get_expected_encrypted_files_content()
    for file in source_files:
        assert expected_encrypted_files[file.name].strip() == file.read_text().strip()
    expected_arguments = {
        "name": "Python Project",
        "description": "",
        "files":[{'name': name, 'content': content} for name, content in expected_encrypted_files.items()],
        "libraries": [],
        "encryption_key": key_hash
    }
    api_client.projects.update.assert_called_once_with(1, **expected_arguments)

def test_cloud_push_decrypted_when_local_files_in_decrypted_state_and_cloud_project_in_encrypted_state_without_key_given() -> None:
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
    expected_arguments = {
        "name": "Python Project",
        "description": "",
        "files": [{'name': 'main.py', 'content': '# region imports\nfrom AlgorithmImports import *\n# endregion\n\nclass PythonProject(QCAlgorithm):\n\n    def initialize(self):\n        # Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data\n        self.set_start_date(2013, 10, 7)  # Set Start Date\n        self.set_end_date(2013, 10, 11)  # Set End Date\n        self.set_cash(100000)  # Set Strategy Cash\n        self.add_equity("SPY", Resolution.MINUTE)\n\n    def on_data(self, data: Slice):\n        """on_data event is the primary entry point for your algorithm. Each new data point will be pumped in here.\n            Arguments:\n                data: Slice object keyed by symbol containing the stock data\n        """\n        if not self.portfolio.invested:\n            self.set_holdings("SPY", 1)\n            self.debug("Purchased Stock")\n'}, {'name': 'research.ipynb', 'content': '{\n    "cells": [\n        {\n            "cell_type": "markdown",\n            "metadata": {},\n            "source": [\n                "![QuantConnect Logo](https://cdn.quantconnect.com/web/i/icon.png)\\n",\n                "<hr>"\n            ]\n        },\n        {\n            "cell_type": "code",\n            "execution_count": null,\n            "metadata": {},\n            "outputs": [],\n            "source": [\n                "# QuantBook Analysis Tool \\n",\n                "# For more information see [https://www.quantconnect.com/docs/v2/our-platform/research/getting-started]\\n",\n                "qb = QuantBook()\\n",\n                "spy = qb.add_equity(\\"SPY\\")\\n",\n                "# Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data \\n",\n                "qb.set_start_date(2013, 10, 11)\\n",\n                "history = qb.history(qb.securities.keys(), 360, Resolution.DAILY)\\n",\n                "\\n",\n                "# Indicator Analysis\\n",\n                "bbdf = qb.indicator(BollingerBands(30, 2), spy.symbol, 360, Resolution.DAILY)\\n",\n                "bbdf.drop(\'standarddeviation\', axis=1).plot()"\n            ]\n        }\n    ],\n    "metadata": {\n        "kernelspec": {\n            "display_name": "Python 3",\n            "language": "python",\n            "name": "python3"\n        }\n    },\n    "nbformat": 4,\n    "nbformat_minor": 2\n}\n'}],
        "libraries": [],
        "encryption_key": ''
    }
    api_client.projects.update.assert_called_once_with(1, **expected_arguments)

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
    cloud_project = create_api_project(1, "Python Project", encrypted=True, encryptionKey={"name":"test", "id": key_hash_y})
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

def test_cloud_push_sets_code_source_id_to_cli() -> None:
    create_fake_lean_cli_directory()
    project_path = Path.cwd() / "Python Project"

    api_client = mock.Mock()
    cloud_project = create_api_project(1, "Python Project")
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    api_client.files.get_all = mock.MagicMock(return_value=[
        QCFullFile(name="file.py", content="print(123)", modified=datetime.now(), isLibrary=False)
    ])

    init_container(api_client_to_use=api_client)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", project_path])

    assert result.exit_code == 0
    expected_arguments = {
        "name": "Python Project",
        "description": "",
        "files": mock.ANY,
        "libraries": [],
        "encryption_key": "",
        "codeSourceId": "cli"
    }
    api_client.projects.update.assert_called_once_with(1, **expected_arguments)
