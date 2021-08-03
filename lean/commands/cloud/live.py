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
from typing import List, Tuple, Optional

import click

from lean.click import LeanCommand, ensure_options
from lean.components.api.api_client import APIClient
from lean.components.util.logger import Logger
from lean.container import container
from lean.models.api import (QCEmailNotificationMethod, QCNode, QCNotificationMethod, QCSMSNotificationMethod,
                             QCWebhookNotificationMethod, QCProject)
from lean.models.brokerages.cloud import all_cloud_brokerages
from lean.models.brokerages.cloud.base import CloudBrokerage
from lean.models.brokerages.cloud.bitfinex import BitfinexBrokerage
from lean.models.brokerages.cloud.coinbase_pro import CoinbaseProBrokerage
from lean.models.brokerages.cloud.interactive_brokers import InteractiveBrokersBrokerage
from lean.models.brokerages.cloud.oanda import OANDABrokerage
from lean.models.brokerages.cloud.paper_trading import PaperTradingBrokerage
from lean.models.brokerages.cloud.tradier import TradierBrokerage
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


def _configure_brokerage(logger: Logger) -> CloudBrokerage:
    """Interactively configures the brokerage to use.

    :param logger: the logger to use
    :return: the cloud brokerage the user configured
    """
    brokerage_options = [Option(id=b, label=b.get_name()) for b in all_cloud_brokerages]
    return logger.prompt_list("Select a brokerage", brokerage_options).build(logger)


def _configure_live_node(logger: Logger, api_client: APIClient, cloud_project: QCProject) -> QCNode:
    """Interactively configures the live node to use.

    :param logger: the logger to use
    :param api_client: the API client to make API requests with
    :param cloud_project: the cloud project the user wants to start live trading for
    :return: the live node the user wants to start live trading on
    """
    nodes = api_client.nodes.get_all(cloud_project.organizationId)

    live_nodes = [node for node in nodes.live if not node.busy]
    if len(live_nodes) == 0:
        raise RuntimeError(
            f"You don't have any live nodes available, you can manage your nodes on https://www.quantconnect.com/organization/{cloud_project.organizationId}/resources")

    node_options = [Option(id=node, label=f"{node.name} - {node.description}") for node in live_nodes]
    return logger.prompt_list("Select a node", node_options)


def _configure_notifications(logger: Logger) -> Tuple[bool, bool, List[QCNotificationMethod]]:
    """Interactively configures how and when notifications should be sent.

    :param logger: the logger to use
    :return: whether notifications must be enabled for order events and insights, and the notification methods
    """
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

    return notify_order_events, notify_insights, notify_methods


def _configure_auto_restart(logger: Logger) -> bool:
    """Interactively configures whether automatic algorithm restarting must be enabled.

    :param logger: the logger to use
    :return: whether automatic algorithm restarting must be enabled
    """
    logger.info("Automatic restarting uses best efforts to restart the algorithm if it fails due to a runtime error")
    logger.info("This can help improve its resilience to temporary errors such as a brokerage API disconnection")
    return click.confirm("Do you want to enable automatic algorithm restarting?", default=True)


@click.command(cls=LeanCommand)
@click.argument("project", type=str)
@click.option("--brokerage",
              type=click.Choice([b.get_name() for b in all_cloud_brokerages], case_sensitive=False),
              help="The brokerage to use")
@click.option("--ib-user-name", type=str, help="Your Interactive Brokers username")
@click.option("--ib-account", type=str, help="Your Interactive Brokers account id")
@click.option("--ib-password", type=str, help="Your Interactive Brokers password")
@click.option("--ib-data-feed",
              type=bool,
              help="Whether the Interactive Brokers price data feed must be used instead of the QuantConnect price data feed")
@click.option("--tradier-account-id", type=str, help="Your Tradier account id")
@click.option("--tradier-access-token", type=str, help="Your Tradier access token")
@click.option("--tradier-environment",
              type=click.Choice(["demo", "real"], case_sensitive=False),
              help="The environment to run in, demo for the Developer Sandbox, real for live trading")
@click.option("--oanda-account-id", type=str, help="Your OANDA account id")
@click.option("--oanda-access-token", type=str, help="Your OANDA API token")
@click.option("--oanda-environment",
              type=click.Choice(["demo", "real"], case_sensitive=False),
              help="The environment to run in, demo for fxTrade Practice, real for fxTrade")
@click.option("--bitfinex-api-key", type=str, help="Your Bitfinex API key")
@click.option("--bitfinex-api-secret", type=str, help="Your Bitfinex API secret")
@click.option("--gdax-api-key", type=str, help="Your Coinbase Pro API key")
@click.option("--gdax-api-secret", type=str, help="Your Coinbase Pro API secret")
@click.option("--gdax-passphrase", type=str, help="Your Coinbase Pro API passphrase")
@click.option("--gdax-environment",
              type=click.Choice(["paper", "live"], case_sensitive=False),
              help="The environment to run in, paper for the sandbox, live for live trading")
@click.option("--node", type=str, help="The name or id of the live node to run on")
@click.option("--auto-restart", type=bool, help="Whether automatic algorithm restarting must be enabled")
@click.option("--notify-order-events", type=bool, help="Whether notifications must be sent for order events")
@click.option("--notify-insights", type=str, help="Whether notifications must be sent for emitted insights")
@click.option("--notify-emails",
              type=str,
              help="A comma-separated list of 'email:subject' pairs configuring email-notifications")
@click.option("--notify-webhooks",
              type=str,
              help="A comma-separated list of 'url:HEADER_1=VALUE_1:HEADER_2=VALUE_2:etc' pairs configuring webhook-notifications")
@click.option("--notify-sms", type=str, help="A comma-separated list of phone numbers configuring SMS-notifications")
@click.option("--push",
              is_flag=True,
              default=False,
              help="Push local modifications to the cloud before starting live trading")
@click.option("--open", "open_browser",
              is_flag=True,
              default=False,
              help="Automatically open the live results in the browser once the deployment starts")
def live(project: str,
         brokerage: str,
         ib_user_name: Optional[str],
         ib_account: Optional[str],
         ib_password: Optional[str],
         ib_data_feed: Optional[bool],
         tradier_account_id: Optional[str],
         tradier_access_token: Optional[str],
         tradier_environment: Optional[str],
         oanda_account_id: Optional[str],
         oanda_access_token: Optional[str],
         oanda_environment: Optional[str],
         bitfinex_api_key: Optional[str],
         bitfinex_api_secret: Optional[str],
         gdax_api_key: Optional[str],
         gdax_api_secret: Optional[str],
         gdax_passphrase: Optional[str],
         gdax_environment: Optional[str],
         node: str,
         auto_restart: bool,
         notify_order_events: Optional[bool],
         notify_insights: Optional[bool],
         notify_emails: Optional[str],
         notify_webhooks: Optional[str],
         notify_sms: Optional[str],
         push: bool,
         open_browser: bool) -> None:
    """Start live trading for a project in the cloud.

    PROJECT must be the name or the id of the project to start live trading for.

    By default an interactive wizard is shown letting you configure the deployment.
    If --brokerage is given the command runs in non-interactive mode.
    In this mode the CLI does not prompt for input or confirmation.
    In non-interactive mode the options specific to the given brokerage are required,
    as well as --node, --auto-restart, --notify-order-events and --notify-insights.
    """
    logger = container.logger()
    api_client = container.api_client()

    cloud_project_manager = container.cloud_project_manager()
    cloud_project = cloud_project_manager.get_cloud_project(project, push)

    cloud_runner = container.cloud_runner()
    finished_compile = cloud_runner.compile_project(cloud_project)

    if brokerage is not None:
        ensure_options(["brokerage", "node", "auto_restart", "notify_order_events", "notify_insights"])

        brokerage_instance = None

        if brokerage == PaperTradingBrokerage.get_name():
            brokerage_instance = PaperTradingBrokerage()
        elif brokerage == InteractiveBrokersBrokerage.get_name():
            ensure_options(["ib_user_name", "ib_account", "ib_password", "ib_data_feed"])
            brokerage_instance = InteractiveBrokersBrokerage(ib_user_name, ib_account, ib_password, ib_data_feed)
        elif brokerage == TradierBrokerage.get_name():
            ensure_options(["tradier_account_id", "tradier_access_token", "tradier_environment"])
            brokerage_instance = TradierBrokerage(tradier_account_id, tradier_access_token, tradier_environment)
        elif brokerage == OANDABrokerage.get_name():
            ensure_options(["oanda_account_id", "oanda_access_token", "oanda_environment"])
            brokerage_instance = OANDABrokerage(oanda_account_id, oanda_access_token, oanda_environment)
        elif brokerage == BitfinexBrokerage.get_name():
            ensure_options(["bitfinex_api_key", "bitfinex_api_secret"])
            brokerage_instance = BitfinexBrokerage(bitfinex_api_key, bitfinex_api_secret)
        elif brokerage == CoinbaseProBrokerage.get_name():
            ensure_options(["gdax_api_key", "gdax_api_secret", "gdax_passphrase", "gdax_environment"])
            brokerage_instance = CoinbaseProBrokerage(gdax_api_key, gdax_api_secret, gdax_passphrase, gdax_environment)

        all_nodes = api_client.nodes.get_all(cloud_project.organizationId)
        live_node = next((n for n in all_nodes.live if n.id == node or n.name == node), None)

        if live_node is None:
            raise RuntimeError(f"You have no live node with name or id '{node}'")

        if live_node.busy:
            raise RuntimeError(f"The live node named '{live_node.name}' is already in use by '{live_node.usedBy}'")

        notify_methods = []

        if notify_emails is not None:
            for config in notify_emails.split(","):
                address, subject = config.split(":")
                notify_methods.append(QCEmailNotificationMethod(address=address, subject=subject))

        if notify_webhooks is not None:
            for config in notify_webhooks.split(","):
                address, *headers = config.split(":")
                headers = {header.split("=")[0]: header.split("=")[1] for header in headers}
                notify_methods.append(QCWebhookNotificationMethod(address=address, headers=headers))

        if notify_sms is not None:
            for phoneNumber in notify_sms.split(","):
                notify_methods.append(QCSMSNotificationMethod(phoneNumber=phoneNumber))
    else:
        brokerage_instance = _configure_brokerage(logger)
        live_node = _configure_live_node(logger, api_client, cloud_project)
        notify_order_events, notify_insights, notify_methods = _configure_notifications(logger)
        auto_restart = _configure_auto_restart(logger)

    brokerage_settings = brokerage_instance.get_settings()
    price_data_handler = brokerage_instance.get_price_data_handler()

    logger.info(f"Brokerage: {brokerage_instance.get_name()}")
    logger.info(f"Project id: {cloud_project.projectId}")
    logger.info(f"Environment: {brokerage_settings['environment'].title()}")
    logger.info(f"Server name: {live_node.name}")
    logger.info(f"Server type: {live_node.sku}")
    logger.info(f"Data provider: {price_data_handler.replace('Handler', '')}")
    logger.info(f"LEAN version: {cloud_project.leanVersionId}")
    logger.info(f"Order event notifications: {'Yes' if notify_order_events else 'No'}")
    logger.info(f"Insight notifications: {'Yes' if notify_insights else 'No'}")
    if notify_order_events or notify_insights:
        _log_notification_methods(notify_methods)
    logger.info(f"Automatic algorithm restarting: {'Yes' if auto_restart else 'No'}")

    if brokerage is None:
        click.confirm(f"Are you sure you want to start live trading for project '{cloud_project.name}'?",
                      default=False,
                      abort=True)

    live_algorithm = api_client.live.start(cloud_project.projectId,
                                           finished_compile.compileId,
                                           live_node.id,
                                           brokerage_settings,
                                           price_data_handler,
                                           auto_restart,
                                           cloud_project.leanVersionId,
                                           notify_order_events,
                                           notify_insights,
                                           notify_methods)

    logger.info(f"Live url: {live_algorithm.get_url()}")

    if open_browser:
        webbrowser.open(live_algorithm.get_url())
