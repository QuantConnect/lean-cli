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

from lean.components.cloud import cloud_runner
from lean.components.cloud.cloud_runner import CloudRunner


def test_confirm_asks_the_user() -> None:
    with mock.patch.object(cloud_runner, "confirm", return_value=False) as confirm, \
            mock.patch("lean.constants.IS_UI_COMMAND", False):
        assert CloudRunner._confirm("Delete?") is False

    confirm.assert_called_once_with("Delete?", True)


def test_confirm_answers_yes_when_run_by_the_ui() -> None:
    with mock.patch.object(cloud_runner, "confirm") as confirm, mock.patch("lean.constants.IS_UI_COMMAND", True):
        assert CloudRunner._confirm("Delete?") is True

    confirm.assert_not_called()
