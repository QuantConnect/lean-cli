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

from enum import Enum
from pathlib import Path

from lean.models.pydantic import WrappedBaseModel

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


class LeanLibraryReference(WrappedBaseModel):
    """The information of a library reference in a project's config.json file"""
    name: str
    path: Path
