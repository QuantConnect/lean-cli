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

from click import group

from lean.commands.config.get import get
from lean.commands.config.list import list
from lean.commands.config.set import set
from lean.commands.config.unset import unset


@group()
def config() -> None:
    """Configure Lean CLI options."""
    # This method is intentionally empty
    # It is used as the command group for all `lean config <command>` commands
    pass


config.add_command(get)
config.add_command(set)
config.add_command(unset)
config.add_command(list)
