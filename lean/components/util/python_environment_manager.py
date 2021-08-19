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

import hashlib
import shutil
import zipfile
from base64 import b64decode
from pathlib import Path

from lean.components.config.storage import Storage
from lean.components.docker.docker_manager import DockerManager
from lean.components.util.http_client import HTTPClient
from lean.components.util.logger import Logger
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.temp_manager import TempManager
from lean.components.util.xml_manager import XMLManager
from lean.constants import PYTHON_ENVIRONMENTS_DIRECTORY
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

        self._environments_dir = Path(PYTHON_ENVIRONMENTS_DIRECTORY)
        self._cache_key = "docker-image-foundation-hashes"

        if not self._environments_dir.is_dir():
            self._environments_dir.mkdir(parents=True)

    def get_environment_directory(self, environment_id: str, image: DockerImage) -> Path:
        """Returns the path to an unpacked environment and downloads it if it doesn't exist yet.

        :param environment_id: the id of the environment to get the path of
        :param image: the image the environment will be used with
        :return: the path to the local directory containing the environment
        """
        if not self.is_environment_installed(environment_id, image):
            self.update_environment(environment_id, image)

        foundation_hash = self._get_foundation_hash(image)

        latest_dir = None
        latest_dir_environment = None

        for directory in self._environments_dir.iterdir():
            environment = PythonEnvironment.parse(directory)

            if environment.foundation_hash != foundation_hash:
                continue

            if latest_dir is None or environment.lean_version > latest_dir_environment.lean_version:
                latest_dir = latest_dir
                latest_dir_environment = environment

        return latest_dir

    def update_environment(self, environment_id: str, image: DockerImage) -> None:
        """Downloads the latest version of a Python environment.

        :param environment_id: the id of the environment to download the latest version of
        :param image: the image with which the environment will be used
        """
        foundation_hash = self._get_foundation_hash(image)

        files_response = self._http_client.get(
            f"http://datastore.quantconnect.com:9001/environments?prefix={foundation_hash}_")
        files_xml = self._xml_manager.parse(files_response.text)
        available_files = [x.text for x in files_xml.findall(".//Contents/Key")]

        latest_zip = None
        latest_zip_environment = None

        for file in available_files:
            if not file.endswith(".zip"):
                continue

            environment = PythonEnvironment.parse(file)

            if environment.foundation_hash != foundation_hash:
                continue

            if latest_zip_environment is None or environment.lean_version > latest_zip_environment.lean_version:
                latest_zip = file
                latest_zip_environment = environment

        if latest_zip is None:
            raise RuntimeError(
                f"Did not find eligible virtual environment for environment '{environment_id}' and foundation hash '{foundation_hash}'")

        final_environment_dir = self._environments_dir / str(latest_zip_environment)
        if final_environment_dir.is_dir():
            return

        download_link = f"http://datastore.quantconnect.com:9001/environments/{latest_zip}"

        tmp_dir = self._temp_manager.create_temporary_directory()
        tmp_archive_file = tmp_dir / f"{latest_zip_environment}.zip"
        tmp_archive_dir = tmp_dir / str(latest_zip_environment)

        self._logger.info(
            f"Downloading Python environment named '{environment_id}' containing common packages, this may take a while...")
        self._http_client.download_file(download_link, tmp_archive_file)

        with zipfile.ZipFile(tmp_archive_file) as zip_file:
            zip_file.extractall(tmp_archive_dir)

        tmp_archive_dir.rename(final_environment_dir)

        self._prune_unused_environments()

    def is_environment_installed(self, environment_id: str, image: DockerImage) -> bool:
        """Checks whether a version of an environment is available for an image.

        This method returns True even if the environment may be outdated.

        :param environment_id: the id of the environment
        :param image: the image with which the environment will be used
        :return: whether a version of the environment is available locally
        """
        foundation_hash = self._get_foundation_hash(image)
        installed_envs = [PythonEnvironment.parse(file) for file in self._environments_dir.iterdir()]
        return any(
            env.foundation_hash == foundation_hash and env.environment_id == environment_id for env in installed_envs)

    def _prune_unused_environments(self) -> None:
        installed_envs = [PythonEnvironment.parse(file) for file in self._environments_dir.iterdir()]
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
                shutil.rmtree(self._environments_dir / str(env), ignore_errors=True)

    def _get_foundation_hash(self, image: DockerImage) -> str:
        image_digest = self._docker_manager.get_local_digest(image)

        cached_mapping = self._cache_storage.get(self._cache_key, {})
        if str(image) in cached_mapping and cached_mapping[str(image)]["image-digest"] == image_digest:
            return cached_mapping[str(image)]["foundation-hash"]

        creation_timestamp = self._docker_manager.get_creation_timestamp(image)
        creation_timestamp = creation_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        commit_response = self._http_client.get(
            f"https://api.github.com/repos/QuantConnect/Lean/commits?per_page=1&until={creation_timestamp}")
        commit_sha = commit_response.json()[0]["sha"]

        foundation_file_name = "DockerfileLeanFoundation"
        if self._platform_manager.is_host_arm():
            foundation_file_name += "ARM"

        file_response = self._http_client.get(
            f"https://api.github.com/repos/QuantConnect/Lean/contents/{foundation_file_name}?ref={commit_sha}")

        # TODO: Update this with how the foundation file is hashed in the cloud
        foundation_bytes = b64decode(file_response.json()["content"].encode("utf-8"))
        foundation_hash = hashlib.md5(foundation_bytes).hexdigest()

        cached_mapping = self._cache_storage.get(self._cache_key, {})
        self._cache_storage.set(self._cache_key, {
            **cached_mapping,
            str(image): {
                "image-digest": image_digest,
                "foundation-hash": foundation_hash
            }
        })

        return foundation_hash
