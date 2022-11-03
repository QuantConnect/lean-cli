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


@command(cls=LeanCommand)
def list() -> None:
    """List the configurable options and their current values."""
    from rich import box
    from rich.table import Table
    table = Table(box=box.SQUARE)
    table.add_column("Key", overflow="fold")
    table.add_column("Value", overflow="fold")
    table.add_column("Location", overflow="fold")
    table.add_column("Description", overflow="fold")

    for option in container.cli_config_manager.all_options:
        value = option.get_value(default="<not set>")

        # Mask values of sensitive options
        if value != "<not set>" and option.is_sensitive:
            value = "*" * 12 + value[-3:] if len(value) >= 5 else "*" * 15

        table.add_row(option.key,
                      value,
                      str(option.location),
                      option.description)

    logger = container.logger
    logger.info(table)
