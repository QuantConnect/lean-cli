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

from click import command

from lean.click import LeanCommand
from lean.container import container


@command(cls=LeanCommand, requires_lean_config=True)
def ui() -> None:
    """Browse projects and run commands on them in an interactive terminal UI.

    \b
    Use the arrow keys or j/k to move, / to filter, enter to pick an action and q to quit.
    """
    # Textual is imported here so it does not slow down the startup of other commands
    from lean.ui.app import LeanApp

    lean_config_manager = container.lean_config_manager
    try:
        data_dir = lean_config_manager.get_data_directory()
    except Exception:
        data_dir = None

    LeanApp(lean_config_manager.get_cli_root_directory(), data_dir).run()
