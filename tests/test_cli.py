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

import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pytest

from lean.components.api.api_client import APIClient
from lean.components.util.logger import Logger

# These tests require a QuantConnect user id and API token
# The credentials can also be provided using the QC_USER_ID and QC_API_TOKEN environment variables

# The tests in this file call the CLI itself to verify it works as expected
# Be aware that these tests change the global CLI configuration on this system

USER_ID = ""
API_TOKEN = ""


@pytest.fixture(autouse=True)
def fake_filesystem() -> None:
    """A pytest fixture which disables the mocking of the filesystem for the tests in this file."""
    return


@pytest.fixture(autouse=True)
def requests_mock() -> None:
    """A pytest fixture which disables the mocking of HTTP requests for the tests in this file."""
    return


def run_command(args: List[str],
                cwd: Optional[Path] = None,
                input: List[str] = [],
                expected_return_code: int = 0,
                expected_output: Optional[str] = None,
                timeout: int = 120) -> str:
    """Runs a command and runs assertions on the return code and output.

    :param args: the command to run
    :param cwd: the directory to run the command in, or None to use the current directory
    :param input: the lines to provide to stdin
    :param expected_return_code: the expected return code of the command
    :param expected_output: the string the output of the command is expected to contain
    :param timeout: the timeout of the command in seconds
    :return: the output of the command
    """
    print(f"Running {args}")

    try:
        process = subprocess.run(args,
                                 cwd=cwd,
                                 input=str.encode("\n".join(input) + "\n"),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 timeout=timeout)
    except subprocess.TimeoutExpired as error:
        print(error.stdout.decode("utf-8"))
        raise error

    output = process.stdout.decode("utf-8")
    print(output)

    assert process.returncode == expected_return_code

    if expected_output is not None:
        assert expected_output in output

    return output


def test_cli() -> None:
    """Tests the CLI by actually calling it like a real user would do.

    Unlike "normal" tests, this file only contains a single test method which steps through all commands.
    This is done on purpose to make the test as close to what real users do as possible.
    """
    user_id = USER_ID or os.getenv("QC_USER_ID", "")
    api_token = API_TOKEN or os.getenv("QC_API_TOKEN", "")

    if user_id == "" or api_token == "":
        pytest.skip("API credentials not specified")

    global_config_path = Path("~/.lean").expanduser()
    credentials_path = global_config_path / "credentials"

    # Create an empty directory to perform tests in
    test_dir = Path(tempfile.mkdtemp())

    # We use project names suffixed by a timestamp to prevent conflicts when we synchronize with the cloud
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    python_project_name = f"Python Project {timestamp}"
    csharp_project_name = f"CSharp Project {timestamp}"

    # Unset all global configuration
    shutil.rmtree(global_config_path, ignore_errors=True)

    # Log in
    run_command(["lean", "login"], input=[user_id, api_token])
    assert credentials_path.exists()
    assert json.loads(credentials_path.read_text(encoding="utf-8")) == {
        "user-id": user_id,
        "api-token": api_token
    }

    # Download sample data and LEAN configuration file
    run_command(["lean", "init"], cwd=test_dir, input=["python"])
    assert (test_dir / "data").is_dir()
    assert (test_dir / "lean.json").is_file()

    # Generate random data
    # This is the first command that uses the LEAN Docker image, so we increase the timeout to have time to pull it
    generate_output = run_command(["lean", "data", "generate",
                                   "--start", "20150101",
                                   "--symbol-count", "1",
                                   "--resolution", "Daily"],
                                  cwd=test_dir,
                                  timeout=600)
    matches = re.findall(
        r"Begin data generation of 1 randomly generated Equity assets\.\.\.\r?\n\s*Symbol\[1]: ([A-Z]+)",
        generate_output)
    assert len(matches) == 1
    assert (test_dir / "data" / "equity" / "usa" / "daily" / f"{matches[0].lower()}.zip").is_file()

    # Configure global settings
    run_command(["lean", "config", "set", "default-language", "csharp"])
    run_command(["lean", "config", "get", "default-language"], expected_output="csharp")
    run_command(["lean", "config", "unset", "default-language"])
    run_command(["lean", "config", "get", "default-language"], expected_return_code=1)
    run_command(["lean", "config", "set", "default-language", "python"])
    run_command(["lean", "config", "get", "default-language"], expected_output="python")
    list_output = run_command(["lean", "config", "list"])
    assert len(re.findall(r"default-language[ ]+[^ ] python", list_output)) == 1

    # Create Python project
    run_command(["lean", "create-project", "--language", "python", python_project_name], cwd=test_dir)
    python_project_dir = test_dir / python_project_name
    assert (python_project_dir / "main.py").is_file()
    assert (python_project_dir / "research.ipynb").is_file()
    assert (python_project_dir / "config.json").is_file()
    assert (python_project_dir / ".vscode" / "launch.json").is_file()
    assert (python_project_dir / ".vscode" / "settings.json").is_file()
    assert (python_project_dir / ".idea" / f"{python_project_name}.iml").is_file()
    assert (python_project_dir / ".idea" / "misc.xml").is_file()
    assert (python_project_dir / ".idea" / "modules.xml").is_file()
    assert (python_project_dir / ".idea" / "workspace.xml").is_file()

    # Create C# project
    run_command(["lean", "create-project", "--language", "csharp", csharp_project_name], cwd=test_dir)
    csharp_project_dir = test_dir / csharp_project_name
    assert (csharp_project_dir / "Main.cs").is_file()
    assert (csharp_project_dir / "research.ipynb").is_file()
    assert (csharp_project_dir / "config.json").is_file()
    assert (csharp_project_dir / f"{csharp_project_name}.csproj").is_file()
    assert (csharp_project_dir / ".vscode" / "launch.json").is_file()

    # Add custom Python library
    run_command(["lean", "library", "add", python_project_name, "altair"], cwd=test_dir)
    assert (python_project_dir / "requirements.txt").is_file()
    assert f"altair==" in (python_project_dir / "requirements.txt").read_text(encoding="utf-8")

    # Cannot add custom Python library incompatible with Python 3.6
    run_command(["lean", "library", "add", python_project_name, "PyS3DE"], cwd=test_dir, expected_return_code=1)

    # Cannot add custom Python library without version when it's not on PyPI
    run_command(["lean", "library", "add", python_project_name, str(uuid.uuid4())],
                cwd=test_dir,
                expected_return_code=1)

    # Cannot add custom Python library with version when version is invalid
    run_command(["lean", "library", "add", python_project_name, "matplotlib", "--version", "0.0.0.0.0.1"],
                cwd=test_dir,
                expected_return_code=1)

    # Cannot add custom Python library with version when version is incompatible with Python 3.6
    run_command(["lean", "library", "add", python_project_name, "matplotlib", "--version", "3.4.2"],
                cwd=test_dir,
                expected_return_code=1)

    # Add custom C# library
    run_command(["lean", "library", "add", csharp_project_name, "Microsoft.ML"], cwd=test_dir)
    csproj_file = csharp_project_dir / f"{csharp_project_name}.csproj"
    assert 'Include="Microsoft.ML"' in csproj_file.read_text(encoding="utf-8")

    # Cannot add custom C# library without version when it's not on NuGet
    run_command(["lean", "library", "add", csharp_project_name, str(uuid.uuid4())],
                cwd=test_dir,
                expected_return_code=1)

    # Copy over algorithms containing a SPY buy-and-hold strategy and which import the custom libraries
    fixtures_dir = Path(__file__).parent / "fixtures"
    shutil.copy(fixtures_dir / "local" / "main.py", python_project_dir / "main.py")
    shutil.copy(fixtures_dir / "local" / "Main.cs", csharp_project_dir / "Main.cs")

    # Backtest Python project locally
    run_command(["lean", "backtest", python_project_name], cwd=test_dir, expected_output="Total Trades 1")
    python_backtest_dirs = list((python_project_dir / "backtests").iterdir())
    assert len(python_backtest_dirs) == 1

    # Backtest C# project locally
    run_command(["lean", "backtest", csharp_project_name], cwd=test_dir, expected_output="Total Trades 1")
    csharp_backtest_dirs = list((csharp_project_dir / "backtests").iterdir())
    assert len(csharp_backtest_dirs) == 1

    # Remove custom Python library
    run_command(["lean", "library", "remove", python_project_name, "altair"], cwd=test_dir)
    assert f"altair==" not in (python_project_dir / "requirements.txt").read_text(encoding="utf-8")

    # Remove custom C# library
    run_command(["lean", "library", "remove", csharp_project_name, "Microsoft.ML"], cwd=test_dir)
    assert 'Include="Microsoft.ML"' not in csproj_file.read_text(encoding="utf-8")

    # Custom Python library is removed, so Python backtest should now fail
    run_command(["lean", "backtest", python_project_name], cwd=test_dir, expected_return_code=1)

    # Custom C# library is removed, so C# backtest should now fail
    run_command(["lean", "backtest", csharp_project_name], cwd=test_dir, expected_return_code=1)

    # Generate report
    run_command(["lean", "report",
                 "--backtest-data-source-file",
                 f"{python_project_name}/backtests/{python_backtest_dirs[0].name}/main.json"],
                cwd=test_dir)
    assert (test_dir / "report.html").is_file()

    # Copy over algorithms containing a SPY buy-and-hold strategy and which don't import the custom libraries
    shutil.copy(fixtures_dir / "cloud" / "main.py", python_project_dir / "main.py")
    shutil.copy(fixtures_dir / "cloud" / "Main.cs", csharp_project_dir / "Main.cs")

    # Push projects to the cloud
    run_command(["lean", "cloud", "push", "--project", python_project_name], cwd=test_dir)
    run_command(["lean", "cloud", "push", "--project", csharp_project_name], cwd=test_dir)

    # Remove some files and see if we can successfully pull them from the cloud
    (python_project_dir / "main.py").unlink()
    (csharp_project_dir / "Main.cs").unlink()

    # Pull projects from the cloud
    run_command(["lean", "cloud", "pull", "--project", python_project_name], cwd=test_dir)
    run_command(["lean", "cloud", "pull", "--project", csharp_project_name], cwd=test_dir)

    # Ensure deleted files have been pulled
    (python_project_dir / "main.py").is_file()
    (csharp_project_dir / "Main.cs").is_file()

    # Run Python backtest in the cloud
    run_command(["lean", "cloud", "backtest", python_project_name], cwd=test_dir)

    # Run C# backtest in the cloud
    run_command(["lean", "cloud", "backtest", csharp_project_name], cwd=test_dir)

    # Log out
    run_command(["lean", "logout"])
    assert not credentials_path.exists()

    # Delete the test directory that we used
    shutil.rmtree(test_dir, ignore_errors=True)

    # Delete the cloud projects that we used
    api_client = APIClient(Logger(), user_id, api_token)
    cloud_projects = api_client.projects.get_all()
    api_client.projects.delete(next(p.projectId for p in cloud_projects if p.name == python_project_name))
    api_client.projects.delete(next(p.projectId for p in cloud_projects if p.name == csharp_project_name))
