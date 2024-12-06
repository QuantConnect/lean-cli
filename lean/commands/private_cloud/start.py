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
from typing import Optional
from json import loads

from click import command, option, prompt
from docker.errors import APIError
from docker.types import Mount

from lean.click import LeanCommand
from lean.commands.private_cloud.stop import get_private_cloud_containers, stop_command
from lean.container import container
from lean.models.cli import cli_compute
from lean.models.docker import DockerImage
from lean.constants import COMPUTE_MASTER, COMPUTE_SLAVE, COMPUTE_MESSAGING


def deploy(target_master_domain: str, self_domain: str, port: int, token: str, slave: bool, update: bool, no_update: bool,
           image: str, lean_config: dict, extra_docker_config: str, counter: int = 0):
    logger = container.logger

    compute_node_name = f"{COMPUTE_SLAVE}{counter}" if slave else COMPUTE_MASTER
    logger.info(f"Starting {compute_node_name}...")
    compute_directory = Path(f"~/.lean/compute/{compute_node_name}").expanduser()
    lean_config["node-name"] = compute_node_name

    run_options = container.lean_runner.get_basic_docker_config_without_algo(lean_config, None, True, None, None,
                                                                             None, compute_directory)
    run_options["environment"]["AIRLOCK"] = compute_directory
    run_options["mounts"].append(Mount(target="/QuantConnect/platform-services/airlock",
                                       source=str(compute_directory), type="bind"))
    run_options["mounts"].append(Mount(target="/var/run/docker.sock", source="/var/run/docker.sock",
                                       type="bind", read_only=True))
    docker_config_source = Path("~/.docker/config.json").expanduser()
    run_options["mounts"].append(Mount(target="/root/.docker/config.json", source=str(docker_config_source),
                                       type="bind", read_only=True))
    container.lean_runner.parse_extra_docker_config(run_options, loads(extra_docker_config))

    if not image:
        image = "quantconnect/platform-services:latest"

    is_domain = not self_domain.replace('.', '').isnumeric()
    if not slave:
        if not is_domain:
            run_options["ports"]["9696"] = str(port)
            run_options["ports"]["9697"] = str(0)

        root_directory = container.lean_config_manager.get_cli_root_directory()
        run_options["volumes"][str(root_directory)] = {"bind": "/LeanCLIWorkspace", "mode": "rw"}

    if is_domain:
        labels = {}
        for name, value in container.docker_manager.get_image_labels(image):
            if slave and name == "slave" or not slave and name == "master":
                for key, label in loads(value).items():
                    labels[key] = label.replace("{{domain}}", self_domain)
        run_options["labels"] = labels

    run_options["remove"] = False
    run_options["name"] = compute_node_name
    run_options["environment"]["MODE"] = str('slave') if slave else str('master')
    run_options["environment"]["MASTER_DOMAIN"] = str(target_master_domain)
    run_options["environment"]["SELF_DOMAIN"] = str(self_domain)
    run_options["environment"]["PORT"] = str(port)
    run_options["environment"]["TOKEN"] = str(token)
    run_options["user"] = "root"
    run_options["restart_policy"] = {"Name": "always"}
    run_options["verify_stability"] = True

    if not image:
        image = "quantconnect/platform-services:latest"
    docker_image = DockerImage.parse(image)
    container.update_manager.pull_docker_image_if_necessary(docker_image, update, no_update)
    try:
        container.docker_manager.run_image(image, **run_options)
    except APIError as error:
        msg = error.explanation
        if isinstance(msg, str) and any(m in msg.lower() for m in [
            "port is already allocated",
            "ports are not available"
            "an attempt was made to access a socket in a way forbidden by its access permissions"
        ]):
            f"Port {port} is already in use, please specify a different port using --master-port <number>"
        raise error


def get_ip_address():
    from socket import gethostname, gethostbyname
    hostname = gethostname()
    return gethostbyname(hostname + ".local")


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True, help="Start a new private cloud")
@option("--master", is_flag=True, default=False, help="Run in master mode")
@option("--slave", is_flag=True, default=False, help="Run in slave mode")
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
def start(master: bool,
          slave: bool,
          token: str,
          master_domain: str,
          slave_domain: str,
          master_port: int,
          update: bool,
          no_update: bool,
          compute: Optional[str],
          extra_docker_config: Optional[str],
          image: Optional[str],
          stop: bool) -> None:
    start_command(master,
                  slave,
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


def start_command(master: bool,
          slave: bool,
          token: str,
          master_domain: str,
          slave_domain: str,
          master_port: int,
          update: bool,
          no_update: bool,
          compute: Optional[str],
          extra_docker_config: Optional[str],
          image: Optional[str],
          stop: bool) -> None:
    logger = container.logger

    if stop:
        stop_command()

    if slave and master:
        raise RuntimeError(f"Can only provide one of '--master' or '--slave'")
    if not slave and not master:
        # just default to slave if none given
        slave = True

    if not master_domain:
        master_domain = prompt("Master domain", get_ip_address())

    str_mode = 'slave' if slave else 'master'
    logger.info(f'Start running in {str_mode} mode')

    if not compute:
        # configure
        compute = []
        for module in cli_compute:
            module.config_build({}, logger, True)
            compute_config = module.get_settings()
            compute.append(compute_config)
    else:
        compute = loads(compute)

    if slave:
        if not token:
            token = prompt("Master token")
    else:
        if not token:
            from uuid import uuid4
            token = uuid4().hex

    docker_container = get_private_cloud_containers()
    if any(docker_container):
        names = [node.name for node in docker_container if node.status == 'running']
        if master and (COMPUTE_MASTER in names or COMPUTE_MESSAGING in names):
            raise RuntimeError(f"Private cloud nodes already running, please use '--stop'. Detected: {names}")
        logger.info(f"Running nodes: {names}")

    container.temp_manager.delete_temporary_directories_when_done = False
    lean_config = container.lean_config_manager.get_complete_lean_config(None, None, None)

    master_is_domain = not master_domain.replace('.', '').isnumeric()
    if master:
        master_port_option = f" --master-port {master_port}"
        if master_is_domain:
            slave_domain = master_domain
            master_port_option = ''
        deploy(master_domain, master_domain, master_port, token, False, update, no_update, image,
               lean_config, extra_docker_config)
        if master_port == 0:
            master_port = container.docker_manager.get_container_port(COMPUTE_MASTER, "9696/tcp")

        logger.info(f"Slaves can be added running: lean private-cloud start --slave --master-domain {master_domain}"
                    f" --slave-domain {{slave.domain}} --token \"{token}\"{master_port_option}")

    compute_index = len(get_private_cloud_containers([COMPUTE_SLAVE]))
    if compute:
        logger.debug(f"Starting given compute configuration: {compute}")

        if not slave_domain:
            logger.debug(f"'slave-domain' was not given will try to figure it out...")
            retry_count = 0
            while retry_count < 10:
                retry_count += 1
                try:
                    from requests import get
                    resp = get(f'http://{master_domain}:{master_port}', stream=True)
                    potential_slave_domain = resp.raw._connection.sock.getsockname()[0]
                    slave_domain = prompt("Slave domain", potential_slave_domain)
                    break
                except Exception as e:
                    from time import sleep
                    sleep(1)
                    pass
        lean_config["self-ip-address"] = slave_domain
        logger.debug(f"Using address '{slave_domain}' as own")

        for configuration in compute:
            lean_config["compute"] = configuration
            for i in range(compute_index, int(configuration["count"]) + compute_index):
                deploy(master_domain, slave_domain, master_port, token, True, update, no_update, image,
                       lean_config, extra_docker_config, i)
