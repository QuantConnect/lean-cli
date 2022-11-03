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
from lean.models.errors import MoreInfoError


@command(cls=LeanCommand)
@argument("key", type=str)
def get(key: str) -> None:
    """Get the current value of a configurable option.

    Sensitive options like credentials cannot be retrieved this way for security reasons.
    Please open ~/.lean/credentials if you want to see your currently stored credentials.

    Run `lean config list` to show all available options.
    """
    cli_config_manager = container.cli_config_manager

    option = cli_config_manager.get_option_by_key(key)
    if option.is_sensitive:
        raise RuntimeError(
            "Sensitive options like credentials cannot be retrieved using `lean config get` for security reasons")

    value = option.get_value()
    if value is None:
        raise MoreInfoError(f"The option with key '{key}' doesn't have a value set",
                            "https://www.lean.io/docs/v2/lean-cli/api-reference/lean-config-set")

    logger = container.logger
    logger.info(value)
