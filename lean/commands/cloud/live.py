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
from typing import List

import click

from lean.click import LeanCommand
from lean.container import container
from lean.models.api import (QCEmailNotificationMethod, QCNode, QCNotificationMethod, QCSMSNotificationMethod,
                             QCWebhookNotificationMethod)
from lean.models.brokerages.cloud import all_cloud_brokerages
from lean.models.logger import Option


def _log_notification_methods(methods: List[QCNotificationMethod]) -> None:
    """Logs a list of notification methods."""
    logger = container.logger()

    email_methods = [method for method in methods if isinstance(method, QCEmailNotificationMethod)]
    email_methods = "None" if len(email_methods) == 0 else ", ".join(method.address for method in email_methods)

    webhook_methods = [method for method in methods if isinstance(method, QCWebhookNotificationMethod)]
    webhook_methods = "None" if len(webhook_methods) == 0 else ", ".join(method.address for method in webhook_methods)

    sms_methods = [method for method in methods if isinstance(method, QCSMSNotificationMethod)]
    sms_methods = "None" if len(sms_methods) == 0 else ", ".join(method.phoneNumber for method in sms_methods)

    logger.info(f"Email notifications: {email_methods}")
    logger.info(f"Webhook notifications: {webhook_methods}")
    logger.info(f"SMS notifications: {sms_methods}")


def _prompt_notification_method() -> QCNotificationMethod:
    """Prompts the user to add a notification method.

    :return: the notification method configured by the user
    """
    logger = container.logger()
    selected_method = logger.prompt_list("Select a notification method", [Option(id="email", label="Email"),
                                                                          Option(id="webhook", label="Webhook"),
                                                                          Option(id="sms", label="SMS")])

    if selected_method == "email":
        address = click.prompt("Email address")
        subject = click.prompt("Subject")
        return QCEmailNotificationMethod(address=address, subject=subject)
    elif selected_method == "webhook":
        address = click.prompt("URL")
        headers = {}

        while True:
            headers_str = "None" if headers == {} else ", ".join(f"{key}={headers[key]}" for key in headers)
            logger.info(f"Headers: {headers_str}")

            if not click.confirm("Do you want to add a header?", default=False):
                break

            key = click.prompt("Header key")
            value = click.prompt("Header value")
            headers[key] = value

        return QCWebhookNotificationMethod(address=address, headers=headers)
    else:
        phone_number = click.prompt("Phone number")
        return QCSMSNotificationMethod(phoneNumber=phone_number)


@click.command(cls=LeanCommand)
@click.argument("project", type=str)
@click.option("--push",
              is_flag=True,
              default=False,
              help="Push local modifications to the cloud before starting live trading")
@click.option("--open", "open_browser",
              is_flag=True,
              default=False,
              help="Automatically open the live results in the browser once the deployment starts")
def live(project: str, push: bool, open_browser: bool) -> None:
    """Start live trading for a project in the cloud.

    An interactive prompt will be shown to configure the deployment.

    PROJECT must be the name or the id of the project to start live trading for.

    If the project that has to be live traded has been pulled to the local drive
    with `lean cloud pull` it is possible to use the --push option to push local
    modifications to the cloud before starting live trading.
    """
    logger = container.logger()
    api_client = container.api_client()

    cloud_project_manager = container.cloud_project_manager()
    cloud_project = cloud_project_manager.get_cloud_project(project, push)

    cloud_runner = container.cloud_runner()
    finished_compile = cloud_runner.compile_project(cloud_project)

    brokerage_options = [Option(id=brokerage, label=brokerage.name) for brokerage in all_cloud_brokerages]

    brokerage = logger.prompt_list("Select a brokerage", brokerage_options)
    brokerage_settings = brokerage.get_settings(logger)
    price_data_handler = brokerage.get_price_data_handler()

    nodes = api_client.nodes.get_all(cloud_project.organizationId)

    live_nodes = [node for node in nodes.live if not node.busy]
    if len(live_nodes) == 0:
        raise RuntimeError(
            f"You don't have any live nodes available, you can manage your nodes on https://www.quantconnect.com/organization/{cloud_project.organizationId}/resources")

    node_options = [Option(id=node, label=f"{node.name} - {node.description}") for node in live_nodes]
    node: QCNode = logger.prompt_list("Select a node", node_options)

    logger.info(
        "You can optionally request for your strategy to send notifications when it generates an order or emits an insight")
    logger.info("You can use any combination of email notifications, webhook notifications and SMS notifications")
    notify_order_events = click.confirm("Do you want to send notifications on order events?", default=False)
    notify_insights = click.confirm("Do you want to send notifications on insights?", default=False)
    notify_methods = []

    if notify_order_events or notify_insights:
        _log_notification_methods(notify_methods)
        notify_methods.append(_prompt_notification_method())

        while True:
            _log_notification_methods(notify_methods)
            if not click.confirm("Do you want to add another notification method?", default=False):
                break
            notify_methods.append(_prompt_notification_method())

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
    logger.info(f"Order event notifications: {'Yes' if notify_order_events else 'No'}")
    logger.info(f"Insight notifications: {'Yes' if notify_insights else 'No'}")
    if notify_order_events or notify_insights:
        _log_notification_methods(notify_methods)
    logger.info(f"Automatic algorithm restarting: {'Yes' if automatic_redeploy else 'No'}")

    click.confirm(f"Are you sure you want to start live trading for project '{cloud_project.name}'?",
                  default=False,
                  abort=True)

    live_algorithm = api_client.live.start(cloud_project.projectId,
                                           finished_compile.compileId,
                                           node.id,
                                           brokerage_settings,
                                           price_data_handler,
                                           automatic_redeploy,
                                           cloud_project.leanVersionId,
                                           notify_order_events,
                                           notify_insights,
                                           notify_methods)

    logger.info(f"Live url: {live_algorithm.get_url()}")

    if open_browser:
        webbrowser.open(live_algorithm.get_url())
