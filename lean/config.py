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


class Config:
    """The Config class contains configuration which is used to configure classes in the container.

    Due to the way the filesystem is mocked in unit tests, values should not be Path instances.
    """
    # The file in which general CLI configuration is stored
    general_config_file = str(Path("~/.lean/config").expanduser())

    # The file in which credentials are stored
    credentials_config_file = str(Path("~/.lean/credentials").expanduser())

    # The default name of the configuration file in a Lean CLI directory
    default_lean_config_file_name = "lean.json"

    # The default name of the data directory in a Lean CLI directory
    default_data_directory_name = "data"

    # The name of the configuration file in a project in a Lean CLI directory
    # This should match the file name expected by https://github.com/QuantConnect/Lean/blob/master/DockerfileJupyter
    project_config_file_name = "config.json"

    # The Docker image used when running the LEAN engine locally
    lean_engine_docker_image = "quantconnect/lean"

    # The Docker image used when running a Jupyter Lab environment locally
    research_docker_image = "quantconnect/research"

    # The base url of the QuantConnect API
    api_base_url = "https://www.quantconnect.com/api/v2"
