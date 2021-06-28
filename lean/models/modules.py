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

import re

from lean.models.pydantic import WrappedBaseModel


class NuGetPackage(WrappedBaseModel):
    name: str
    version: str

    def get_file_name(self) -> str:
        """Returns the file name of the package.

        :return: the file name of the NuGet package
        """
        return f"{self.name}.{self.version}.nupkg"

    @classmethod
    def parse(cls, file_name: str) -> 'NuGetPackage':
        """Parses a file name into a NuGetPackage instance.

        :param file_name: the file name of the NuGet package
        :return: the NuGetPackage instance containing the name and version of the package with the given file name
        """
        name = re.search(r"([^\d]+)\.\d", file_name).group(1)
        version = file_name.replace(f"{name}.", "").replace(".nupkg", "")

        return NuGetPackage(name=name, version=version)
