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
from lean.container import container


def test_logout_deletes_credentials_storage_file() -> None:
    container.cli_config_manager().user_id.set_value("123")
    assert Path("~/.lean/credentials").expanduser().exists()

    result = CliRunner().invoke(lean, ["logout"])

    assert result.exit_code == 0

    assert not Path("~/.lean/credentials").expanduser().exists()
