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

from lean.components.config.lean_config_manager import LeanConfigManager

def open_storage_directory_in_explorer(lean_config_manager: LeanConfigManager):
    """Opens the storage directory in the file explorer."""
    global_storage_directory_path = lean_config_manager.get_cli_root_directory() / "storage"
    if not global_storage_directory_path.exists():
        global_storage_directory_path.mkdir(parents=True)
    open_file_explorer(str(global_storage_directory_path))
    
def open_file_explorer(directory_path: str):
    """Opens the given directory in the file explorer."""
    from webbrowser import open
    open('file:///' + directory_path)