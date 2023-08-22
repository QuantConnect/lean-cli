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


from lean.commands.object_store.get import get
from lean.commands.object_store.set import set
from lean.commands.object_store.list import list
from lean.commands.object_store.delete import delete

@group()
def object_store() -> None:
    """Interact with the Organization's Object Store."""
    # This method is intentionally empty
    # It is used as the command group for all `lean object-store <command>` commands
    pass


object_store.add_command(get)
object_store.add_command(set)
object_store.add_command(list)
object_store.add_command(delete)

