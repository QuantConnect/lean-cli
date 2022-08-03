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
from lean.components.util.click_group_default_command import DefaultCommandGroup
from lean.constants import COMMAND_FILE_BASENAME, COMMAND_RESULT_FILE_BASENAME
import time
from pathlib import Path

@click.group(cls=DefaultCommandGroup)
def live() -> None:
    """Interact with the local machine."""
    # This method is intentionally empty
    # It is used as the command group for all `lean cloud <command>` commands
    pass

def get_command_file_name():
    return Path(f'{COMMAND_FILE_BASENAME}-{int(time.time())}.json')

def get_result_file_name(command_id: str):
    return Path(f'{COMMAND_RESULT_FILE_BASENAME}-{command_id}.json')