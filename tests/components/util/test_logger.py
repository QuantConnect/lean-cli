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

from unittest import mock

from _pytest.capture import CaptureFixture

from lean.components.util.logger import Logger
from lean.models.logger import Option


def assert_stdout_stderr(capsys: CaptureFixture, stdout: str, stderr: str) -> None:
    out, err = capsys.readouterr()
    assert out == stdout
    assert err == stderr


def test_debug_does_not_log_until_debug_logging_is_enabled(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.debug("Message 1")
    logger.debug_logging_enabled = True
    logger.debug("Message 2")

    assert_stdout_stderr(capsys, "Message 2\n", "")


def test_debug_logs_message(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.debug_logging_enabled = True
    logger.debug("Message")

    assert_stdout_stderr(capsys, "Message\n", "")


def test_info_logs_message(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.info("Message")

    assert_stdout_stderr(capsys, "Message\n", "")


def test_warn_logs_message(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.warn("Message")

    assert_stdout_stderr(capsys, "Message\n", "")


def test_error_logs_message(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.error("Message")

    assert_stdout_stderr(capsys, "Message\n", "")


def test_progress_creates_started_progress_instance(capsys: CaptureFixture) -> None:
    logger = Logger()
    progress = logger.progress()

    result = progress._started

    progress.stop()
    assert result

    capsys.readouterr()


@mock.patch("click.prompt")
def test_prompt_list_returns_id_of_selected_option(prompt: mock.Mock, capsys: CaptureFixture) -> None:
    logger = Logger()
    options = [Option(id=1, label="Option 1"), Option(id=2, label="Option 2"), Option(id=3, label="Option 3")]

    prompt.return_value = 3
    selected_option = logger.prompt_list("Select an option", options)

    assert selected_option == 3

    capsys.readouterr()


@mock.patch("click.prompt")
def test_prompt_list_displays_all_options(prompt: mock.Mock, capsys: CaptureFixture) -> None:
    logger = Logger()
    options = [Option(id=1, label="Option 1"), Option(id=2, label="Option 2"), Option(id=3, label="Option 3")]

    prompt.return_value = 3
    logger.prompt_list("Select an option", options)

    stdout, stderr = capsys.readouterr()
    assert "Option 1" in stdout
    assert "Option 2" in stdout
    assert "Option 3" in stdout


def test_prompt_returns_single_option_without_prompting_with_display_of_value(capsys: CaptureFixture) -> None:
    logger = Logger()
    options = [Option(id=1, label="Option 1")]

    selected_option = logger.prompt_list("Select an option", options)

    assert selected_option == 1

    stdout, stderr = capsys.readouterr()
    assert "Select an option: Option 1" in stdout
