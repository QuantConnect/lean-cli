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

import click

from lean.commands.gui.logs import logs
from lean.commands.gui.restart import restart
from lean.commands.gui.start import start
from lean.commands.gui.stop import stop


@click.group()
def gui() -> None:
    """Work with the local GUI."""
    # This method is intentionally empty
    # It is used as the command group for all `lean gui <command>` commands
    pass


gui.add_command(start)
gui.add_command(restart)
gui.add_command(stop)
gui.add_command(logs)
