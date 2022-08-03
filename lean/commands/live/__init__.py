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

from lean.commands.live.live import live
from lean.commands.live.deploy import deploy
from lean.commands.live.stop import stop
from lean.commands.live.liquidate import liquidate
from lean.commands.live.submit_order import submit_order
from lean.commands.live.cancel_order import cancel_order
from lean.commands.live.add_security import add_security
from lean.commands.live.update_order import update_order

live.add_command(deploy)
live.add_command(stop)
live.add_command(liquidate)
live.add_command(submit_order)
live.add_command(cancel_order)
live.add_command(add_security)
live.add_command(update_order)