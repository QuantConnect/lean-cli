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


class KrakenBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Kraken."""

    def __init__(self, api_key: str, secret_key: str, verification_tier: str) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._verification_tier = verification_tier

    @classmethod
    def get_id(cls) -> str:
        return "KrakenBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "Kraken"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        logger.info("""
Create an API key by logging in and accessing the Kraken API Management page (https://www.kraken.com/u/security/api).
        """.strip())

        api_key = click.prompt("API key")
        secret_key = logger.prompt_password("Secret key")
        verification_tier = click.prompt("Verification Tier")

        return KrakenBrokerage(api_key, secret_key, verification_tier)

    def _get_settings(self) -> Dict[str, str]:
        return {
            "key": self._api_key,
            "secret": self._secret_key,
            "verificationTier": self._verification_tier,
            "environment": "live"
        }
