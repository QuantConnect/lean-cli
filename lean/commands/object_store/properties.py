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
from lean.components.util.object_store_helper import open_storage_directory_in_explorer


@command(cls=LeanCommand)
def properties() -> str:
    """
    Opens the local storage directory in the file explorer.
    """
    open_storage_directory_in_explorer(container.lean_config_manager)
