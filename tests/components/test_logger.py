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

from _pytest.capture import CaptureFixture

from lean.components.logger import Logger


def assert_stdout_stderr(capsys: CaptureFixture, stdout: str, stderr: str) -> None:
    out, err = capsys.readouterr()
    assert out == stdout
    assert err == stderr


def test_debug_does_not_log_until_debug_logging_is_enabled(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.debug("Message 1")
    logger.enable_debug_logging()
    logger.debug("Message 2")

    assert_stdout_stderr(capsys, "Message 2\n", "")


def test_debug_logs_message_to_stdout(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.enable_debug_logging()
    logger.debug("Message")

    assert_stdout_stderr(capsys, "Message\n", "")


def test_info_logs_message_to_stdout(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.info("Message")

    assert_stdout_stderr(capsys, "Message\n", "")


def test_warn_logs_message_to_stderr(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.warn("Message")

    assert_stdout_stderr(capsys, "", "Message\n")


def test_error_logs_message_to_stderr(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.error("Message")

    assert_stdout_stderr(capsys, "", "Message\n")
