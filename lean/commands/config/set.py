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

from click import command, argument
from lean.click import LeanCommand
from lean.container import container


@command(cls=LeanCommand)
@argument("key", type=str)
@argument("value", type=str)
def set(key: str, value: str) -> None:
    """Set a configurable option.

    Run `lean config list` to show all available options.
    """
    cli_config_manager = container.cli_config_manager

    option = cli_config_manager.get_option_by_key(key)
    option.set_value(value)

    logger = container.logger
    logger.info(f"Successfully updated the value of '{key}' to '{option.get_value()}'")
