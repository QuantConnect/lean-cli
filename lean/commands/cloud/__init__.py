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

from lean.commands.cloud.backtest import backtest
from lean.commands.cloud.live import live
from lean.commands.cloud.optimize import optimize
from lean.commands.cloud.pull import pull
from lean.commands.cloud.push import push
from lean.commands.cloud.status import status


@click.group()
def cloud() -> None:
    """Interact with the QuantConnect cloud."""
    # This method is intentionally empty
    # It is used as the command group for all `lean cloud <command>` commands
    pass


cloud.add_command(pull)
cloud.add_command(push)
cloud.add_command(backtest)
cloud.add_command(optimize)
cloud.add_command(live)
cloud.add_command(status)
