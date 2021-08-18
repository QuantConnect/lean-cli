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

import os
from datetime import datetime, timezone
from pathlib import Path

# Due to the way the filesystem is mocked in unit tests, values should not be Path instances.

# The file in which general CLI configuration is stored
GENERAL_CONFIG_PATH = str(Path("~/.lean/config").expanduser())

# The file in which credentials are stored
CREDENTIALS_CONFIG_PATH = str(Path("~/.lean/credentials").expanduser())

# The file in which we store when we last checked for updates
CACHE_PATH = str(Path("~/.lean/cache").expanduser())

# The directory in which modules are stored
MODULES_DIRECTORY = str(Path("~/.lean/modules").expanduser())

# The default name of the file containing the Lean engine configuration
DEFAULT_LEAN_CONFIG_FILE_NAME = "lean.json"

# The default name of the directory containing the market data
DEFAULT_DATA_DIRECTORY_NAME = "data"

# The name of the file in containing the project configuration
PROJECT_CONFIG_FILE_NAME = "config.json"

# The default Docker image used when running the LEAN engine locally
DEFAULT_ENGINE_IMAGE = "quantconnect/lean:latest"

# The default Docker image used when running a Jupyter Lab environment locally
DEFAULT_RESEARCH_IMAGE = "quantconnect/research:latest"

# When we install custom Python libraries, we first mount a volume to the user site packages directory
# This caches the installation and makes subsequent backtests much faster
# Because the site packages are not versioned, we cannot reuse the volume between algorithms with different requirements
# This constant defines how many site packages volumes get created before old ones are removed
SITE_PACKAGES_VOLUME_LIMIT = 10

# The base url of the QuantConnect API
# This url should end with a forward slash
_qc_api = os.environ.get("QC_API", "")
if _qc_api == "local":
    API_BASE_URL = "http://localhost:5612/api/v2/"
elif _qc_api == "beta":
    API_BASE_URL = "https://beta.quantconnect.com/api/v2/"
else:
    API_BASE_URL = "https://www.quantconnect.com/api/v2/"

# The interval in hours at which the CLI checks for updates to itself
UPDATE_CHECK_INTERVAL_CLI = 24

# The interval in hours at which the CLI checks for updates to Docker images that are being ran
UPDATE_CHECK_INTERVAL_DOCKER_IMAGE = 24 * 7

# The interval in hours at which the CLI checks for new announcements
UPDATE_CHECK_INTERVAL_ANNOUNCEMENTS = 24

# The product id of the Security Master subscription
SECURITY_MASTER_PRODUCT_ID = 37

# The product id of the Bloomberg module
BLOOMBERG_PRODUCT_ID = 44

# The product id of the Trading Technologies module
TRADING_TECHNOLOGIES_PRODUCT_ID = 64

# The product id of the Atreyu module
ATREYU_PRODUCT_ID = 65

# The product id of the GUI module
GUI_PRODUCT_ID = 119

# The name of the Docker network which all Lean CLI containers are ran on
DOCKER_NETWORK = "lean_cli"

# The name of the Docker container running the local GUI
LOCAL_GUI_CONTAINER_NAME = "lean_cli_gui"
