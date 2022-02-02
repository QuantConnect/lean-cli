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

from typing import Dict

import click

from lean.components.util.logger import Logger
from lean.models.brokerages.cloud.base import CloudBrokerage


class ZerodhaBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Zerodha."""

    def __init__(self, api_key: str, access_token: str, product_type: str, trading_segment: str) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._product_type = product_type
        self._trading_segment = trading_segment

    @classmethod
    def get_id(cls) -> str:
        return "ZerodhaBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "Zerodha"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        logger.info("""
Create an API key by logging in and accessing the Zerodha API Management page (https://kite.trade/).
        """.strip())

        api_key = click.prompt("API key")
        access_token = logger.prompt_password("Access Token")
        product_type = click.prompt("Product type", type=click.Choice(["MIS", "CNC", "NRML"], case_sensitive=False))
        trading_segment = click.prompt("Trading segment", type=click.Choice(["EQUITY", "COMMODITY"], case_sensitive=False))

        return ZerodhaBrokerage(api_key, access_token, product_type, trading_segment)

    def _get_settings(self) -> Dict[str, str]:
        return {
            "key": self._api_key,
            "accessToken": self._access_token,
            "productType": self._product_type,
            "tradingSegment": self._trading_segment,
            "environment": "live"
        }
