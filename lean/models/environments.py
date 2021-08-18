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

from pathlib import Path
from typing import Union

from lean.models.pydantic import WrappedBaseModel


class PythonEnvironment(WrappedBaseModel):
    foundation_hash: str
    requirements_hash: str
    environment_id: str
    lean_version: int

    @classmethod
    def parse(cls, file: Union[Path, str]) -> 'PythonEnvironment':
        """Parses the Python environment components from a file path.

        :param file: the path to extract the environment information from
        :return: a PythonEnvironment object containing the information about the environment in the given path
        """
        if isinstance(file, Path):
            file = file.name
        else:
            file = file.split("/")[-1]

        file = file.replace(".zip", "")

        # TODO: Update this when the actual file names are known
        foundation_hash, requirements_hash, environment_id, lean_version = file.split("_")

        return PythonEnvironment(foundation_hash=foundation_hash,
                                 requirements_hash=requirements_hash,
                                 environment_id=environment_id,
                                 lean_version=int(lean_version))

    def __str__(self) -> str:
        """Returns the full name of the virtual environment without extension.

        :return: the full name of the virtual environment without extension
        """
        return f"{self.foundation_hash}_{self.requirements_hash}_{self.environment_id}_{self.lean_version}"
