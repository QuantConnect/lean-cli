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
from lean.models.brokerages.cloud.ftx import FTXBrokerage


class FTXUSBrokerage(FTXBrokerage):
    """A CloudBrokerage implementation for FTXUS brokerage."""

    def __init__(self, api_key: str, secret_key: str, account_tier: str) -> None:
        super().__init__(api_key, secret_key, account_tier)

    @classmethod
    def get_id(cls) -> str:
        return "FTXUSBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "FTXUS"

    @classmethod
    def get_domain(cls) -> str:
        return "ftx.us"

    @classmethod
    def create_brokerage(cls, api_key: str, secret_key: str, account_tier: str) -> CloudBrokerage:
        return FTXUSBrokerage(api_key, secret_key, account_tier)