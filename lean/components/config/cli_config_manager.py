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

from typing import Optional

from lean.components.config.storage import Storage
from lean.constants import DEFAULT_ENGINE_IMAGE, DEFAULT_RESEARCH_IMAGE
from lean.models.docker import DockerImage
from lean.models.errors import MoreInfoError
from lean.models.options import ChoiceOption, Option


class CLIConfigManager:
    """The CLIConfigManager class contains all configurable CLI options."""

    def __init__(self, general_storage: Storage, credentials_storage: Storage) -> None:
        """Creates a new CLIConfigManager instance.

        :param general_storage: the Storage instance for general, non-sensitive options
        :param credentials_storage: the Storage instance for credentials
        """
        self.user_id = Option("user-id",
                              "The user id used when making authenticated requests to the QuantConnect API.",
                              True,
                              credentials_storage)

        self.api_token = Option("api-token",
                                "The API token used when making authenticated requests to the QuantConnect API.",
                                True,
                                credentials_storage)

        self.default_language = ChoiceOption("default-language",
                                             "The default language used when creating new projects.",
                                             ["python", "csharp"],
                                             False,
                                             general_storage)

        self.engine_image = Option("engine-image",
                                   f"The Docker image used when running the LEAN engine ({DEFAULT_ENGINE_IMAGE} if not set).",
                                   False,
                                   general_storage)

        self.research_image = Option("research-image",
                                     f"The Docker image used when running the research environment ({DEFAULT_RESEARCH_IMAGE} if not set).",
                                     False,
                                     general_storage)

        self.all_options = [
            self.user_id,
            self.api_token,
            self.default_language,
            self.engine_image,
            self.research_image
        ]

    def get_option_by_key(self, key: str) -> Option:
        """Returns the option matching the given key.

        If no option with the given key exists, an error is raised.

        :param key: the key to look for
        :return: the option having a key equal to the given key
        """
        option = next((x for x in self.all_options if x.key == key), None)

        if option is None:
            raise MoreInfoError(f"There doesn't exist an option with key '{key}'",
                                "https://www.lean.io/docs/lean-cli/api-reference/lean-config-set#02-Description")

        return option

    def get_engine_image(self, override: Optional[str] = None) -> DockerImage:
        """Returns the LEAN engine image to use.

        :param override: the image name to use, overriding any defaults or previously configured options
        :return: the image that should be used when running the LEAN engine
        """
        return self._get_image_name(self.engine_image, DEFAULT_ENGINE_IMAGE, override)

    def get_research_image(self, override: Optional[str] = None) -> DockerImage:
        """Returns the LEAN research image to use.

        :param override: the image name to use, overriding any defaults or previously configured options
        :return: the image that should be used when running the research environment
        """
        return self._get_image_name(self.research_image, DEFAULT_RESEARCH_IMAGE, override)

    def _get_image_name(self, option: Option, default: str, override: Optional[str]) -> DockerImage:
        """Returns the image to use.

        :param option: the CLI option that configures the image type
        :param override: the image name to use, overriding any defaults or previously configured options
        :param default: the default image to use when the option is not set and no override is given
        :return: the image to use
        """
        if override is not None:
            image = override
        else:
            image = option.get_value(default)

        return DockerImage.parse(image)
