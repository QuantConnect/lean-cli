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
import os
import platform
import signal
import subprocess
import sys
import threading
import types
from pathlib import Path

import docker
from dateutil.parser import isoparse
from docker.errors import APIError
from docker.types import Mount
from getmac import get_mac_address

from lean.components.util.logger import Logger
from lean.components.util.temp_manager import TempManager
from lean.constants import DEFAULT_ENGINE_IMAGE, DOTNET_5_IMAGE_CREATED_TIMESTAMP, SITE_PACKAGES_VOLUME_LIMIT
from lean.models.docker import DockerImage
from lean.models.errors import MoreInfoError


class DockerManager:
    """The DockerManager contains methods to manage and run Docker images."""

    def __init__(self, logger: Logger, temp_manager: TempManager) -> None:
        """Creates a new DockerManager instance.

        :param logger: the logger to use when printing messages
        :param temp_manager: the TempManager instance used when creating temporary directories
        """
        self._logger = logger
        self._temp_manager = temp_manager

    def pull_image(self, image: DockerImage) -> None:
        """Pulls a Docker image.

        :param image: the image to pull
        """
        self._logger.info(f"Pulling {image}...")

        # We cannot really use docker_client.images.pull() here as it doesn't let us log the progress
        # Downloading multiple gigabytes without showing progress does not provide good developer experience
        # Since the pull command is the same on Windows, macOS and Linux we can safely use a system call
        process = subprocess.run(["docker", "image", "pull", str(image)])

        if process.returncode != 0:
            raise RuntimeError(
                f"Something went wrong while pulling {image}, see the logs above for more information")

    def run_image(self, image: DockerImage, **kwargs) -> bool:
        """Runs a Docker image. If the image is not available locally it will be pulled first.

        See https://docker-py.readthedocs.io/en/stable/containers.html for all the supported kwargs.

        If kwargs contains an "on_output" property, it is removed before passing it on to docker.containers.run
        and the given lambda is ran whenever the Docker container prints anything.

        If kwargs contains a "commands" property, it is removed before passing it on to docker.containers.run
        and the Docker container is configured to run the given commands.
        This property causes the "entrypoint" property to be overwritten if it exists.

        :param image: the image to run
        :param kwargs: the kwargs to forward to docker.containers.run
        :return: True if the command in the container exited successfully, False if not
        """
        if not self.image_installed(image):
            self.pull_image(image)

        on_output = kwargs.pop("on_output", lambda chunk: None)
        commands = kwargs.pop("commands", None)

        if commands is not None:
            shell_script_path = self._temp_manager.create_temporary_directory() / "lean-cli-start.sh"
            with shell_script_path.open("w+", encoding="utf-8", newline="\n") as file:
                file.write("\n".join(["#!/usr/bin/env bash", "set -e"] + commands) + "\n")

            if "mounts" not in kwargs:
                kwargs["mounts"] = []

            kwargs["mounts"].append(Mount(target="/lean-cli-start.sh",
                                          source=str(shell_script_path),
                                          type="bind",
                                          read_only=True))
            kwargs["entrypoint"] = ["bash", "/lean-cli-start.sh"]

        # Docker Toolbox requires paths to be like /c/Path instead of C:/Path
        is_windows = platform.system() == "Windows"
        is_docker_toolbox = "machine/machines" in os.environ.get("DOCKER_CERT_PATH", "").replace("\\", "/")
        if is_windows and is_docker_toolbox:
            if "mounts" in kwargs:
                for mount in kwargs["mounts"]:
                    mount["Source"] = self._format_path_docker_toolbox(mount["Source"])

            if "volumes" in kwargs:
                for key in list(kwargs["volumes"].keys()):
                    new_key = self._format_path_docker_toolbox(key)
                    kwargs["volumes"][new_key] = kwargs["volumes"].pop(key)

        is_tty = sys.stdout.isatty()

        kwargs["detach"] = True
        kwargs["hostname"] = platform.node()
        kwargs["tty"] = is_tty
        kwargs["stdin_open"] = is_tty
        kwargs["stop_signal"] = kwargs.get("stop_signal", "SIGKILL")

        mac_address = get_mac_address()
        if mac_address is not None and mac_address != "00:00:00:00:00:00":
            kwargs["mac_address"] = mac_address

        # Make sure host.docker.internal resolves on Linux
        # See https://github.com/QuantConnect/Lean/pull/5092
        if platform.system() == "Linux":
            if "extra_hosts" not in kwargs:
                kwargs["extra_hosts"] = {}
            kwargs["extra_hosts"]["host.docker.internal"] = "172.17.0.1"

        self._logger.debug(f"Running '{image}' with the following configuration:")
        self._logger.debug(kwargs)

        docker_client = self._get_docker_client()
        container = docker_client.containers.run(str(image), None, **kwargs)

        force_kill_next = False
        killed = False

        def kill_container(force: bool) -> None:
            nonlocal killed
            killed = True
            try:
                if force:
                    container.kill()
                else:
                    container.stop(timeout=60)
                container.remove()
            except APIError:
                pass
            finally:
                self._temp_manager.delete_temporary_directories()
                sys.exit(1)

        # Kill the container on Ctrl+C
        def signal_handler(sig: signal.Signals, frame: types.FrameType) -> None:
            nonlocal force_kill_next
            if not is_tty or force_kill_next or kwargs["stop_signal"] == "SIGKILL":
                force_kill_current = True
            else:
                self._logger.info("Waiting 1 minute for LEAN to exit gracefully, press Ctrl+C again to force stop")
                force_kill_next = True
                force_kill_current = False

            # If we run this code on the current thread, a second Ctrl+C won't be detected on Windows
            kill_thread = threading.Thread(target=kill_container, args=[force_kill_current])
            kill_thread.daemon = True
            kill_thread.start()

        signal.signal(signal.SIGINT, signal_handler)

        # container.logs() is blocking, we run it on a separate thread so the SIGINT handler works properly
        # If we run this code on the current thread, SIGINT won't be triggered on Windows when Ctrl+C is triggered
        def print_logs() -> None:
            chunk_buffer = bytes()

            # Capture all logs and print it to stdout line by line
            for chunk in container.logs(stream=True, follow=True):
                chunk_buffer += chunk

                if not chunk_buffer.endswith(b"\n"):
                    continue

                chunk = chunk_buffer.decode("utf-8")
                chunk_buffer = bytes()

                if on_output is not None:
                    on_output(chunk)

                self._logger.info(chunk.rstrip())

                if not is_tty:
                    continue

                if "Press any key to exit..." in chunk or "QuantConnect.Report.Main(): Completed." in chunk:
                    socket = docker_client.api.attach_socket(container.id, params={"stdin": 1, "stream": 1})

                    if hasattr(socket, "_sock"):
                        socket._sock.send(b"\n")
                    else:
                        socket.send(b"\n")

                    socket.close()

        logs_thread = threading.Thread(target=print_logs)
        logs_thread.daemon = True
        logs_thread.start()

        while logs_thread.is_alive():
            logs_thread.join(0.1)

        if killed:
            try:
                container.remove()
            except APIError:
                pass
            finally:
                sys.exit(1)

        container.wait()

        container.reload()
        success = container.attrs["State"]["ExitCode"] == 0

        container.remove()
        return success

    def build_image(self, root: Path, dockerfile: Path, target: DockerImage) -> None:
        """Builds a Docker image.

        :param root: the path build from
        :param dockerfile: the path to the Dockerfile to build
        :param target: the target name and tag
        """
        # We cannot really use docker_client.images.build() here as it doesn't let us log the progress
        # Building images without showing progress does not provide good developer experience
        # Since the build command is the same on Windows, macOS and Linux we can safely use a system call
        process = subprocess.run(["docker", "build", "-t", str(target), "-f", str(dockerfile), "."], cwd=root)

        if process.returncode != 0:
            raise RuntimeError(
                f"Something went wrong while building '{dockerfile}', see the logs above for more information")

    def image_installed(self, image: DockerImage) -> bool:
        """Returns whether a certain image is installed.

        :param image: the image to check availability for
        :return: True if the image is available locally, False if not
        """
        docker_client = self._get_docker_client()
        return any(str(image) in x.tags for x in docker_client.images.list())

    def get_local_digest(self, image: DockerImage) -> str:
        """Returns the digest of a locally installed image.

        :param image: the local image to get the digest of
        :return: the digest of the local image
        """
        img = self._get_docker_client().images.get(str(image))
        return img.attrs["RepoDigests"][0].split("@")[1]

    def get_remote_digest(self, image: DockerImage) -> str:
        """Returns the digest of a remote image.

        :param image: the remote image to get the digest of
        :return: the digest of the remote image
        """
        img = self._get_docker_client().images.get_registry_data(str(image))
        return img.attrs["Descriptor"]["digest"]

    def create_volume(self, name: str) -> None:
        """Creates a new volume, or does nothing if a volume with the given name already exists.

        :param name: the name of the volume to create
        """
        docker_client = self._get_docker_client()
        if not any(v.name == name for v in docker_client.volumes.list()):
            docker_client.volumes.create(name)

    def create_site_packages_volume(self, requirements_file: Path) -> str:
        """Returns the name of the volume to mount to the user's site-packages directory.

        This method automatically returns the best volume for the given requirements.
        It also rotates out older volumes as needed to ensure we don't use too much disk space.

        :param requirements_file: the path to the requirements file that will be pip installed in the container
        :return: the name of the Docker volume to use
        """
        requirements_hash = hashlib.md5(requirements_file.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        volume_name = f"lean_cli_python_{requirements_hash}"

        docker_client = self._get_docker_client()
        existing_volumes = [v for v in docker_client.volumes.list() if v.name.startswith("lean_cli_python_")]

        if any(v.name == volume_name for v in existing_volumes):
            return volume_name

        volumes_by_age = sorted(existing_volumes, key=lambda v: isoparse(v.attrs["CreatedAt"]))
        for i in range((len(volumes_by_age) - SITE_PACKAGES_VOLUME_LIMIT) + 1):
            volumes_by_age[i].remove()

        docker_client.volumes.create(volume_name)
        return volume_name

    def is_missing_permission(self) -> bool:
        """Returns whether we cannot connect to the Docker client because of a permissions issue.

        A permissions issue usually indicates that the client can only be used with root privileges.

        :return: True if we cannot connect to the Docker client because of a permissions issue, False if that's not
        """
        try:
            docker.from_env()
        except Exception as exception:
            return "Permission denied" in str(exception)
        return False

    def supports_dotnet_5(self, image: DockerImage) -> bool:
        """Returns whether an image supports .NET 5 based on its creation date.

        :return: True if we think the image supports .NET 5, False if not or if the tag is not installed
        """
        # We can't make guesses on non-default images
        if str(image) != DEFAULT_ENGINE_IMAGE and str(image) != DEFAULT_ENGINE_IMAGE:
            return True

        for img in self._get_docker_client().images.list():
            if str(image) in img.tags:
                return isoparse(img.attrs["Created"]) >= DOTNET_5_IMAGE_CREATED_TIMESTAMP
        return False

    def _get_docker_client(self) -> docker.DockerClient:
        """Creates a DockerClient instance.

        Raises an error if Docker is not running.

        :return: a DockerClient instance which responds to requests
        """
        error = MoreInfoError("Please make sure Docker is installed and running",
                              "https://www.lean.io/docs/lean-cli/user-guides/troubleshooting#02-Common-errors")

        try:
            docker_client = docker.from_env()
        except Exception:
            raise error

        try:
            if not docker_client.ping():
                raise error
        except Exception:
            raise error

        return docker_client

    def _format_path_docker_toolbox(self, path: str) -> str:
        """Formats a Windows path to make it compatible with Docker Toolbox.

        :param path: the original path
        :return: the original path formatted in such a way that it works with Docker Toolbox
        """
        # Backward slashes to forward slashes
        path = path.replace('\\', '/')

        # C:/Path to /c/Path
        return f"/{path[0].lower()}/{path[3:]}"
