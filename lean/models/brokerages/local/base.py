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

import abc
from typing import Any, Dict

from lean.components.util.logger import Logger
from lean.models.config import LeanConfigConfigurer


class LocalBrokerage(LeanConfigConfigurer, abc.ABC):
    """The LocalBrokerage class is the base class extended for all local brokerages."""

    _instance = None

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        if cls._instance is None:
            cls._instance = cls._build(lean_config, logger)
        return cls._instance

    @classmethod
    @abc.abstractmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> 'LocalBrokerage':
        """Builds a new instance of this class, prompting the user for input when necessary.

        LocalBrokerage.build() ensures this method is called at most once per brokerage.

        :param lean_config: the Lean configuration dict to read defaults from
        :param logger: the logger to use
        """
        raise NotImplementedError()

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self._configure_environment(lean_config, environment_name)
        self.configure_credentials(lean_config)

    @abc.abstractmethod
    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        """Configures the environment in the Lean config for this brokerage.

        :param lean_config: the Lean configuration dict to write to
        :param environment_name: the name of the environment to update
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        """Configures the credentials in the Lean config for this brokerage and saves them persistently to disk.

        :param lean_config: the Lean configuration dict to write to
        """
        raise NotImplementedError()
