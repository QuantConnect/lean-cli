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
from typing import Optional

from click import option, command

from lean.click import LeanCommand
from lean.commands.private_cloud.start import start_command


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True, help="Add private cloud compute")
@option("--token", type=str, required=False, help="The master server token")
@option("--master-domain", "--master-ip", type=str, required=False, help="The master server domain")
@option("--master-port", type=int, required=False, default=443, help="The master server port")
@option("--slave-domain", "--slave-ip", type=str, required=False, help="The slave server domain")
@option("--update", is_flag=True, default=False, help="Pull the latest image before starting")
@option("--no-update", is_flag=True, default=False, help="Do not update to the latest version")
@option("--compute", type=str, required=False, help="Compute configuration to use")
@option("--extra-docker-config", type=str, default="{}", help="Extra docker configuration as a JSON string")
@option("--image", type=str, hidden=True)
@option("--stop", is_flag=True, default=False, help="Stop any existing deployment")
def add_compute(token: str,
                master_domain: str,
                slave_domain: str,
                master_port: int,
                update: bool,
                no_update: bool,
                compute: Optional[str],
                extra_docker_config: Optional[str],
                image: Optional[str],
                stop: bool) -> None:
    start_command(False,
                  True,
                  token,
                  master_domain,
                  slave_domain,
                  master_port,
                  update,
                  no_update,
                  compute,
                  extra_docker_config,
                  image,
                  stop)
