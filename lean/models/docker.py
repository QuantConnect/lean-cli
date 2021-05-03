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

from lean.models.pydantic import WrappedBaseModel


class DockerImage(WrappedBaseModel):
    name: str
    tag: str

    @classmethod
    def parse(cls, image: str) -> 'DockerImage':
        """Parses an image string into a name and a tag.

        :param image: the input value
        :return: the DockerImage object containing the name and the tag of the image
        """
        if ":" in image:
            name, tag = image.split(":")
        else:
            name = image
            tag = "latest"

        return DockerImage(name=name, tag=tag)

    def __str__(self) -> str:
        """Returns the full name of the image.

        :return: the full name of the image in name:tag format
        """
        return f"{self.name}:{self.tag}"
