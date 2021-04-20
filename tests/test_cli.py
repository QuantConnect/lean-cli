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
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pytest

# The tests in this file call the CLI itself to verify it works as expected
# Be aware that these tests change the global CLI configuration on this system

# These tests require a QuantConnect user id and API token
# The credentials can also be provided using the QC_USER_ID and QC_API_TOKEN environment variables
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
                expected_output: Optional[str] = None) -> None:
    """Runs a CLI command and fails the test if the exit code is not 0.

    :param args: the arguments to pass to the CLI
    :param cwd: the directory to run the command in, or None to use the current directory
    :param input: the lines to provide to stdin
    :param expected_return_code: the expected return code of the command
    :param expected_output: the string the output of the command is expected to contain
    """
    args = ["lean"] + args

    print(f"\nRunning {args}")

    process = subprocess.Popen(args, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process.stdin.write(str.encode("\n".join(input) + "\n"))
    process.stdin.close()

    lines = []

    for line in process.stdout:
        print(line.decode("utf-8").strip())
        lines.append(line.decode("utf-8"))

    assert process.wait() == expected_return_code

    if expected_output is not None:
        assert expected_output in "\n".join(lines)


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
    run_command(["login"], input=[user_id, api_token])
    assert credentials_path.exists()
    assert json.loads(credentials_path.read_text(encoding="utf-8")) == {
        "user-id": user_id,
        "api-token": api_token
    }

    # Download sample data and LEAN configuration file
    run_command(["init"], cwd=test_dir, input=["python"])
    assert (test_dir / "data").is_dir()
    assert (test_dir / "lean.json").is_file()

    # Create Python project
    run_command(["create-project", "--language", "python", python_project_name], cwd=test_dir)
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
    run_command(["create-project", "--language", "csharp", csharp_project_name], cwd=test_dir)
    csharp_project_dir = test_dir / csharp_project_name
    assert (csharp_project_dir / "Main.cs").is_file()
    assert (csharp_project_dir / "research.ipynb").is_file()
    assert (csharp_project_dir / "config.json").is_file()
    assert (csharp_project_dir / f"{csharp_project_name}.csproj").is_file()
    assert (csharp_project_dir / ".vscode" / "launch.json").is_file()
    assert (csharp_project_dir / ".idea" / f".idea.{csharp_project_name}" / ".idea" / "workspace.xml").is_file()
    assert (csharp_project_dir / ".idea" / f".idea.{csharp_project_name}.dir" / ".idea" / "workspace.xml").is_file()

    # Copy over algorithms containing a SPY buy-and-hold strategy
    fixtures_dir = Path(__file__).parent / "fixtures"
    shutil.copy(fixtures_dir / "main.py", python_project_dir / "main.py")
    shutil.copy(fixtures_dir / "Main.cs", csharp_project_dir / "Main.cs")

    # Backtest Python project
    run_command(["backtest", python_project_name], cwd=test_dir, expected_output="Total Trades 1")

    # Backtest C# project
    run_command(["backtest", csharp_project_name], cwd=test_dir, expected_output="Total Trades 1")

    # Push projects
    run_command(["cloud", "push", "--project", python_project_name], cwd=test_dir)
    run_command(["cloud", "push", "--project", csharp_project_name], cwd=test_dir)

    # Remove some files and see if we can successfully pull them from the cloud
    (python_project_dir / "main.py").unlink()
    (csharp_project_dir / "Main.cs").unlink()

    # Pull projects
    run_command(["cloud", "pull", "--project", python_project_name], cwd=test_dir)
    run_command(["cloud", "pull", "--project", csharp_project_name], cwd=test_dir)

    # Ensure deleted files have been pulled
    (python_project_dir / "main.py").is_file()
    (csharp_project_dir / "Main.cs").is_file()

    # Log out
    run_command(["logout"])
    assert not credentials_path.exists()

    # Delete the test directory that we used
    shutil.rmtree(test_dir, ignore_errors=True)
