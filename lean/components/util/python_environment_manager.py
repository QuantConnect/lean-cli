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
from lean.components.docker.docker_manager import DockerManager
from lean.components.util.http_client import HTTPClient
from lean.components.util.logger import Logger
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.temp_manager import TempManager
from lean.components.util.xml_manager import XMLManager
from lean.models.docker import DockerImage
from lean.models.environments import PythonEnvironment


class PythonEnvironmentManager:
    """The PythonEnvironmentManager class provides utilities for downloading Python virtual environments."""

    def __init__(self,
                 logger: Logger,
                 http_client: HTTPClient,
                 docker_manager: DockerManager,
                 temp_manager: TempManager,
                 platform_manager: PlatformManager,
                 xml_manager: XMLManager,
                 cache_storage: Storage) -> None:
        """Creates a new PythonEnvironmentManager instance.

        :param logger: the logger to use
        :param http_client: the HTTPClient to use
        :param docker_manager: the DockerManager to use
        :param temp_manager: the TempManager to use
        :param platform_manager: the PlatformManager to use
        :param xml_manager: the XMLManager to use
        :param cache_storage: the Storage instance to store image digest -> foundation hash mappings in
        """
        self._logger = logger
        self._http_client = http_client
        self._docker_manager = docker_manager
        self._temp_manager = temp_manager
        self._platform_manager = platform_manager
        self._xml_manager = xml_manager
        self._cache_storage = cache_storage

        self._cache_key = "docker-image-foundation-hashes"

    def get_environment_volume(self, environment_id: str, image: DockerImage) -> Optional[str]:
        """Returns the path to an unpacked environment and downloads it if it doesn't exist yet.

        :param environment_id: the id of the environment to get the path of
        :param image: the image the environment will be used with
        :return: the path to the volume containing the environment, or None if there is no environment for the given environment id and image
        """
        if not self.is_environment_installed(environment_id, image):
            self.update_environment(environment_id, image)

        foundation_hash = self._get_foundation_hash(image)
        if foundation_hash is None:
            return None

        latest_volume = None
        latest_volume_environment = None

        for volume in self._docker_manager.get_volumes():
            environment = PythonEnvironment.parse(volume)
            if environment is None:
                continue

            if environment.foundation_hash != foundation_hash:
                continue

            if latest_volume is None or environment.lean_version > latest_volume_environment.lean_version:
                latest_volume = volume
                latest_volume_environment = environment

        return latest_volume

    def update_environment(self, environment_id: str, image: DockerImage) -> None:
        """Downloads the latest version of a Python environment.

        :param environment_id: the id of the environment to download the latest version of
        :param image: the image with which the environment will be used
        """
        foundation_hash = self._get_foundation_hash(image)
        if foundation_hash is None:
            return

        files_response = self._http_client.get(
            f"http://datastore.quantconnect.com:9001/environments?prefix={foundation_hash}_")
        files_xml_text = files_response.text.replace('xmlns="http://s3.amazonaws.com/doc/2006-03-01/"', "")
        files_xml = self._xml_manager.parse(files_xml_text)
        available_files = [x.text for x in files_xml.findall(".//Contents/Key")]

        latest_zip = None
        latest_zip_environment = None

        for file in available_files:
            if not file.endswith(".zip"):
                continue

            environment = PythonEnvironment.parse(file)

            if environment.foundation_hash != foundation_hash or environment.environment_id != environment_id:
                continue

            if latest_zip_environment is None or environment.lean_version > latest_zip_environment.lean_version:
                latest_zip = file
                latest_zip_environment = environment

        if latest_zip is None:
            return

        environment_volume = str(latest_zip_environment)
        if environment_volume in self._docker_manager.get_volumes():
            return

        download_link = f"http://datastore.quantconnect.com:9001/environments/{latest_zip}"

        tmp_dir = self._temp_manager.create_temporary_directory()
        tmp_archive_file = tmp_dir / f"{latest_zip_environment}.zip"
        tmp_archive_dir = tmp_dir / str(latest_zip_environment)

        self._logger.info(
            f"Downloading Python environment named '{environment_id}' containing common packages, this may take a while...")
        self._http_client.download_file(download_link, tmp_archive_file)

        self._logger.info(f"Unpacking Python environment named '{environment_id}'")

        try:
            # On Windows unzipping doesn't preserve permissions and symlinks
            # We unzip in a Linux container to a volume to have consistent behavior between platforms
            self._docker_manager.create_volume(environment_volume)
            success = self._docker_manager.run_image(image,
                                                     commands=[
                                                         f"mv /work/{tmp_archive_file.name} /tmp/{tmp_archive_file.name}",
                                                         "cd /tmp",
                                                         f"time unzip -q /tmp/{tmp_archive_file.name}",
                                                         "shopt -s dotglob",
                                                         f"mv /tmp/{tmp_archive_dir.name}/* /output"
                                                     ],
                                                     volumes={
                                                         str(tmp_dir): {
                                                             "bind": "/work",
                                                             "mode": "rw"
                                                         },
                                                         environment_volume: {
                                                             "bind": "/output",
                                                             "mode": "rw"
                                                         }
                                                     })

            if not success:
                self._docker_manager.remove_volume(environment_volume)
        except (Exception, KeyboardInterrupt) as e:
            self._docker_manager.remove_volume(environment_volume)
            raise e

        self._prune_unused_environments()

    def is_environment_installed(self, environment_id: str, image: DockerImage) -> bool:
        """Checks whether a version of an environment is available for an image.

        This method returns True even if the environment may be outdated.

        :param environment_id: the id of the environment
        :param image: the image with which the environment will be used
        :return: whether a version of the environment is available locally
        """
        foundation_hash = self._get_foundation_hash(image)
        if foundation_hash is None:
            return False

        installed_envs = [PythonEnvironment.parse(file) for file in self._docker_manager.get_volumes()]
        installed_envs = [env for env in installed_envs if env is not None]
        return any(
            env.foundation_hash == foundation_hash and env.environment_id == environment_id for env in installed_envs)

    def _prune_unused_environments(self) -> None:
        installed_envs = [PythonEnvironment.parse(file) for file in self._docker_manager.get_volumes()]
        installed_envs = [env for env in installed_envs if env is not None]
        used_envs = []

        cached_mapping = self._cache_storage.get(self._cache_key, {})
        for obj in cached_mapping.values():
            foundation_hash = obj["foundation-hash"]
            used_env_ids = {env.environment_id for env in installed_envs if env.foundation_hash == foundation_hash}

            for env_id in used_env_ids:
                eligible_envs = [env for env in installed_envs
                                 if env.foundation_hash == foundation_hash and env.environment_id == env_id]
                used_envs.append(max(eligible_envs, key=lambda env: env.lean_version))

        for env in installed_envs:
            if env not in used_envs:
                self._docker_manager.remove_volume(str(env))

    def _get_foundation_hash(self, image: DockerImage) -> Optional[str]:
        image_id = self._docker_manager.get_local_id(image)

        cached_mapping = self._cache_storage.get(self._cache_key, {})
        if str(image) in cached_mapping and cached_mapping[str(image)]["image-id"] == image_id:
            return cached_mapping[str(image)]["foundation-hash"]

        environment_variables = self._docker_manager.get_environment_variables(image)
        foundation_hash = environment_variables.get("LEAN_FOUNDATION_VERSION", None)

        cached_mapping = self._cache_storage.get(self._cache_key, {})
        self._cache_storage.set(self._cache_key, {
            **cached_mapping,
            str(image): {
                "image-id": image_id,
                "foundation-hash": foundation_hash
            }
        })

        return foundation_hash
