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

from pathlib import Path

# Due to the way the filesystem is mocked in unit tests, values should not be Path instances.

# The file in which general CLI configuration is stored
GENERAL_CONFIG_PATH = str(Path("~/.lean/config").expanduser())

# The file in which credentials are stored
CREDENTIALS_CONFIG_PATH = str(Path("~/.lean/credentials").expanduser())

# The file in which we store when we last checked for updates
CACHE_PATH = str(Path("~/.lean/cache").expanduser())

# The default name of the file containing the Lean engine configuration
DEFAULT_LEAN_CONFIG_FILE_NAME = "lean.json"

# The default name of the directory containing the market data
DEFAULT_DATA_DIRECTORY_NAME = "data"

# The name of the file in containing the project configuration
PROJECT_CONFIG_FILE_NAME = "config.json"

# The Docker image used when running the LEAN engine locally
ENGINE_IMAGE = "quantconnect/lean"

# The Docker image used when running a Jupyter Lab environment locally
RESEARCH_IMAGE = "quantconnect/research"

# The base url of the QuantConnect API
# This url should end with a forward slash
API_BASE_URL = "https://www.quantconnect.com/api/v2/"

# The interval in hours at which the CLI checks for updates to itself
UPDATE_CHECK_INTERVAL_CLI = 24

# The interval in hours at which the CLI checks for updates to Docker images that are being ran
UPDATE_CHECK_INTERVAL_DOCKER_IMAGE = 24 * 14
