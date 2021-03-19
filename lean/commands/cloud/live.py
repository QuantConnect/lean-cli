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

import webbrowser
from pathlib import Path

import click

from lean.click import LeanCommand
from lean.container import container
from lean.models.api import QCNode
from lean.models.brokerages import (BitfinexBrokerage, CloudBrokerage, CoinbaseProBrokerage, FXCMBrokerage,
                                    InteractiveBrokersBrokerage, OANDABrokerage, PaperTradingBrokerage)
from lean.models.logger import Option


@click.command(cls=LeanCommand)
@click.argument("project", type=str)
@click.option("--push",
              is_flag=True,
              default=False,
              help="Push local modifications to the cloud before starting live trading")
@click.option("--open", "open_browser",
              is_flag=True,
              default=False,
              help="Automatically open the live results in the browser once the project has been deployed")
def live(project: str, push: bool, open_browser: bool) -> None:
    """Start live trading for a project in the cloud.

    An interactive prompt will be shown to configure the deployment.

    PROJECT should be the name or id of a cloud project.

    If the project that has to be live traded has been pulled to the local drive
    with `lean cloud pull` it is possible to use the --push option to push local
    modifications to the cloud before starting live trading.
    """
    logger = container.logger()

    api_client = container.api_client()
    all_projects = api_client.projects.get_all()

    for p in all_projects:
        if str(p.projectId) == project or p.name == project:
            cloud_project = p
            break
    else:
        raise RuntimeError("No project with the given name or id exists in the cloud")

    if push:
        local_path = Path.cwd() / cloud_project.name
        if local_path.exists():
            push_manager = container.push_manager()
            push_manager.push_projects([local_path])
        else:
            logger.info(f"'{cloud_project.name}' does not exist locally, not pushing anything")

    cloud_runner = container.cloud_runner()
    finished_compile = cloud_runner.compile_project(cloud_project)

    brokerages = [
        PaperTradingBrokerage(),
        InteractiveBrokersBrokerage(),
        FXCMBrokerage(),
        OANDABrokerage(),
        BitfinexBrokerage(),
        CoinbaseProBrokerage()
    ]

    brokerage_options = [Option(id=brokerage, label=brokerage.name) for brokerage in brokerages]

    brokerage: CloudBrokerage = logger.prompt_list("Select a brokerage", brokerage_options)
    brokerage_settings = brokerage.get_settings(logger)
    price_data_handler = brokerage.get_price_data_handler()

    organization = api_client.accounts.get_organization()
    nodes = api_client.nodes.get_all(organization.organizationId)

    live_nodes = [node for node in nodes.live if not node.busy]
    if len(live_nodes) == 0:
        raise RuntimeError("You don't have any live nodes available")

    node_options = [Option(id=node, label=f"{node.name} - {node.description}") for node in nodes.live]
    node: QCNode = logger.prompt_list("Select a node", node_options)

    logger.info("Automatic restarting uses best efforts to restart the algorithm if it fails due to a runtime error")
    logger.info("This can help improve its resilience to temporary errors such as a brokerage API disconnection")
    automatic_redeploy = click.confirm("Do you want to enable automatic algorithm restarting?", default=True)

    logger.info(f"Brokerage: {brokerage.name}")
    logger.info(f"Project id: {cloud_project.projectId}")
    logger.info(f"Environment: {brokerage_settings['environment'].title()}")
    logger.info(f"Server name: {node.name}")
    logger.info(f"Server type: {node.sku}")
    logger.info(f"Data provider: {price_data_handler.replace('Handler', '')}")
    logger.info(f"LEAN version: {cloud_project.leanVersionId}")

    click.confirm(f"Are you sure you want to start live trading for project '{cloud_project.name}'?",
                  default=False,
                  abort=True)

    api_client.live.start(cloud_project.projectId,
                          finished_compile.compileId,
                          node.id,
                          brokerage_settings,
                          price_data_handler,
                          automatic_redeploy,
                          cloud_project.leanVersionId)

    live_url = cloud_project.get_url().replace("#open", "#openLive")
    logger.info(f"Live url: {live_url}")

    if open_browser:
        webbrowser.open(live_url)
