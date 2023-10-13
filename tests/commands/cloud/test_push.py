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

    push_manager.push_project.assert_called_once_with(Path.cwd() / "Python Project")


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

    cloud_project = create_api_project(1, "Python Project")
    api_client = mock.Mock()
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="removed_file.py", content="", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)
    api_client.files.delete = mock.Mock()

    api_client.projects.get_all = mock.MagicMock(return_value=[cloud_project])
    api_client.projects.get = mock.MagicMock(return_value=create_api_project(1, "Python Project"))

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(side_effect=[None, "Python", "", {}, -1, None, []])

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    project_manager = mock.Mock()
    project_manager.get_source_files = mock.MagicMock(return_value=[])
    project_manager.get_project_libraries = mock.MagicMock(return_value=[])

    push_manager = PushManager(mock.Mock(), api_client, project_manager, project_config_manager, mock.Mock())

    init_container(push_manager_to_use=push_manager, api_client_to_use=api_client)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    project_config.set.assert_called_with("organization-id", "123")


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
        "files": [{'name': 'main.py', 'content': 'ACt9qaSIRLLpdckQHMuT8U+kuh8RR+pK74GN9h4RhxS3P5rEDbyr8Wk82vJzK3Sfv3w8Iny9wmO7yjxD\noHXL2uiPa4nQ/WybaAgKOYkLY3SqHdXD1JvzHVDv3c4AiprHbocXzoiFoNlLjJEArCZ99cPVHObtV8O+\ntJOyJH8fTaOvfR2H3R2rJAf1PzIgx+sHNp/1T021kRQ+Mn/cKTLY+ijFou4TQLBOQEdwKY5pjnogWmK+\nLInQWHO4inBesrtU5Xl2btuGcbmoDC0xs0CRIQLx6w9h/2Dn4Df2Abz59T3p60Ng8/LsfVARYrIdG7EC\nshLjhOzyhhIx/F2NOEBLM1eXRbpq1bA2WgQea9ag1FlKUE/aJml/KRpQgD4i0bl4Kgc6/+HM9khQNxIQ\nzECYECCQv3TmX28FJVnpmmErGMTAvw/H1XowwQFU79VW17ewFGYaaMfiLwZREvc6sbmwcB9LU25Qqpz5\n5HjEpZL4hQd++nW7pusV9ACxFN8EssX4Va/K4LlBsW4O+dIFPFPKZQchvrAjo+6EX3azOgY89sHU2xLL\nyAlkSsBQBBoAqbLl02BMy6b728gXlhW/vY9zl5g7tF4HbG6nUc3XYzjICUitLKVZrCZDpX2EUDqjj8q/\nzuFrJEJOiKConZRn/kRh00l+AXkGEZ9x08/1sbGFGEbjxhobTS1WrrK2q+8NL8Thp+xqaRO9vKCEKtQc\nIDp3/sTD1DCaQOB0nudqy79V7i8TdnoKRMdE8i8ZeTpypQD4e6cv7JcDKZLAv12bmRPf5yn1Q/TZXI4f\n9zEPyBHApK6/9QKqh8QsgGgDRWma9na5BY7lnlkF0bKSGShmWQtHuNDw7lkHbsKPz/3mYBHJM5IWDdwk\nfHVr8j6+qQrj91uzIaAr/tVIP4IPT2RYRVOKJckrvaIvnpoKrhw2YxNkpcPMADmaCOa2RPAc1IovYPGK\n8FD79JNfpfF9uH+g6faIuoGEM5YG3mqx7//p+oLMF2IiaiuW8QN92SyOumgH3jYF3Hl/pSmoJox/waTY\ndDaHg4//NCb05yL+wN4YUqryHd9NJdOYUXcyxjiU8F2DJOrVsOcuhrZPPJbyXu1kxIxG+qszX6Z+evD4\nKvoYxv9/onbZKl7f4W5xjykBHos9QXn5IyMPIc/IOp0ZoGG8I5cDRQnK8n1WWw66dyDmJyV+yeY='}, {'name': 'research.ipynb', 'content': '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'}],
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
        "files": [{'name': 'main.py', 'content': 'ACt9qaSIRLLpdckQHMuT8U+kuh8RR+pK74GN9h4RhxS3P5rEDbyr8Wk82vJzK3Sfv3w8Iny9wmO7yjxD\noHXL2uiPa4nQ/WybaAgKOYkLY3SqHdXD1JvzHVDv3c4AiprHbocXzoiFoNlLjJEArCZ99cPVHObtV8O+\ntJOyJH8fTaOvfR2H3R2rJAf1PzIgx+sHNp/1T021kRQ+Mn/cKTLY+ijFou4TQLBOQEdwKY5pjnogWmK+\nLInQWHO4inBesrtU5Xl2btuGcbmoDC0xs0CRIQLx6w9h/2Dn4Df2Abz59T3p60Ng8/LsfVARYrIdG7EC\nshLjhOzyhhIx/F2NOEBLM1eXRbpq1bA2WgQea9ag1FlKUE/aJml/KRpQgD4i0bl4Kgc6/+HM9khQNxIQ\nzECYECCQv3TmX28FJVnpmmErGMTAvw/H1XowwQFU79VW17ewFGYaaMfiLwZREvc6sbmwcB9LU25Qqpz5\n5HjEpZL4hQd++nW7pusV9ACxFN8EssX4Va/K4LlBsW4O+dIFPFPKZQchvrAjo+6EX3azOgY89sHU2xLL\nyAlkSsBQBBoAqbLl02BMy6b728gXlhW/vY9zl5g7tF4HbG6nUc3XYzjICUitLKVZrCZDpX2EUDqjj8q/\nzuFrJEJOiKConZRn/kRh00l+AXkGEZ9x08/1sbGFGEbjxhobTS1WrrK2q+8NL8Thp+xqaRO9vKCEKtQc\nIDp3/sTD1DCaQOB0nudqy79V7i8TdnoKRMdE8i8ZeTpypQD4e6cv7JcDKZLAv12bmRPf5yn1Q/TZXI4f\n9zEPyBHApK6/9QKqh8QsgGgDRWma9na5BY7lnlkF0bKSGShmWQtHuNDw7lkHbsKPz/3mYBHJM5IWDdwk\nfHVr8j6+qQrj91uzIaAr/tVIP4IPT2RYRVOKJckrvaIvnpoKrhw2YxNkpcPMADmaCOa2RPAc1IovYPGK\n8FD79JNfpfF9uH+g6faIuoGEM5YG3mqx7//p+oLMF2IiaiuW8QN92SyOumgH3jYF3Hl/pSmoJox/waTY\ndDaHg4//NCb05yL+wN4YUqryHd9NJdOYUXcyxjiU8F2DJOrVsOcuhrZPPJbyXu1kxIxG+qszX6Z+evD4\nKvoYxv9/onbZKl7f4W5xjykBHos9QXn5IyMPIc/IOp0ZoGG8I5cDRQnK8n1WWw66dyDmJyV+yeY='}, {'name': 'research.ipynb', 'content': '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'}],
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
