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


class SamcoBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Samco."""

    def __init__(self, client_id: str, client_password: str, year_of_birth: str, product_type: str, trading_segment: str) -> None:
        self._client_id = client_id
        self._client_password = client_password
        self._year_of_birth = year_of_birth
        self._product_type = product_type
        self._trading_segment = trading_segment

    @classmethod
    def get_id(cls) -> str:
        return "SamcoBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "Samco"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        client_id = click.prompt("Client ID")
        client_password = logger.prompt_password("Client Password")
        year_of_birth = click.prompt("Year of Birth")
        product_type = click.prompt("Product type", type=click.Choice(["MIS", "CNC", "NRML"], case_sensitive=False))
        trading_segment = click.prompt("Trading segment", type=click.Choice(["EQUITY", "COMMODITY"], case_sensitive=False))

        return SamcoBrokerage(client_id, client_password, year_of_birth, product_type, trading_segment)

    def _get_settings(self) -> Dict[str, str]:
        return {
            "id": self._client_id,
            "password": self._client_password,
            "yob": self._year_of_birth,
            "productType": self._product_type,
            "tradingSegment": self._trading_segment,
            "environment": "live"
        }
