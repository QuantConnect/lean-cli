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

from typing import Any, Dict

from lean.components.util.logger import Logger
from lean.models.brokerages.local.base import LocalBrokerage


class PaperTradingBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the paper trading brokerage."""

    @classmethod
    def get_name(cls) -> str:
        return "Paper Trading"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        return PaperTradingBrokerage()

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "PaperBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BacktestingTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        pass
