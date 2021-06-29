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
from enum import Enum
from typing import Any, Dict, List, Optional

from lean.components.util.logger import Logger
from lean.models.pydantic import WrappedBaseModel


class LeanConfigConfigurer(abc.ABC):
    """The LeanConfigConfigurer class is the base class extended by all classes that update the Lean config."""

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """Returns the user-friendly name which users can identify this object by.

        :return: the user-friendly name to display to users
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        """Configures the Lean configuration for this brokerage.

        If the Lean configuration has been configured for this brokerage before, nothing will be changed.
        Non-environment changes are saved persistently to disk so they can be used as defaults later.

        :param lean_config: the configuration dict to write to
        :param environment_name: the name of the environment to configure
        """
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> 'LeanConfigConfigurer':
        """Builds a new instance of this class, prompting the user for input when necessary.

        :param lean_config: the Lean configuration dict to read defaults from
        :param logger: the logger to use
        :return: a LeanConfigConfigurer instance containing all the details needed to configure the Lean config
        """
        raise NotImplementedError()

    @classmethod
    def _get_default(cls, lean_config: Dict[str, Any], key: str) -> Optional[Any]:
        """Returns the default value for a property based on the current Lean configuration.

        :param lean_config: the current Lean configuration
        :param key: the name of the property
        :return: the default value for the property, or None if there is none
        """
        if key not in lean_config or lean_config[key] == "":
            return None

        return lean_config[key]

    def _save_properties(self, lean_config: Dict[str, Any], properties: List[str]) -> None:
        """Persistently save properties in the Lean configuration.

        :param lean_config: the dict containing all properties
        :param properties: the names of the properties to save persistently
        """
        from lean.container import container
        container.lean_config_manager().set_properties({key: lean_config[key] for key in properties})


class DebuggingMethod(Enum):
    """The debugging methods supported by the CLI."""
    PyCharm = 1
    PTVSD = 2
    VSDBG = 3
    Rider = 4

    def get_internal_name(self) -> str:
        """Returns the LEAN debugging method that should be used for the current enum member.

        :return: a valid LEAN debugging method that should be used for the current enum member
        """
        return {
            DebuggingMethod.PyCharm: "PyCharm",
            DebuggingMethod.PTVSD: "PTVSD"
        }.get(self, "LocalCmdline")


class CSharpLibrary(WrappedBaseModel):
    """The information of a PackageReference tag in a .csproj file."""
    name: str
    version: str
