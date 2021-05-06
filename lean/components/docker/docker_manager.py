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

import pprint
import signal
import subprocess
import sys
import threading
import types
from pathlib import Path

import docker

from lean.components.util.logger import Logger
from lean.models.docker import DockerImage
from lean.models.errors import MoreInfoError


class DockerManager:
    """The DockerManager contains methods to manage and run Docker images."""

    def __init__(self, logger: Logger) -> None:
        """Creates a new DockerManager instance.

        :param logger: the logger to use when printing messages
        """
        self._logger = logger

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

        If kwargs contains an "on_run" property, it is removed before passing it on to docker.containers.run
        and the given lambda is ran when the Docker container has started.

        :param image: the image to run
        :param kwargs: the kwargs to forward to docker.containers.run
        :return: True if the command in the container exited successfully, False if not
        """
        self._logger.debug(f"Running '{image}' with the following configuration:")
        self._logger.debug(pprint.pformat(kwargs, compact=True))

        if not self.image_installed(image):
            self.pull_image(image)

        on_run = kwargs.pop("on_run", lambda: None)

        docker_client = self._get_docker_client()

        kwargs["detach"] = True
        kwargs["remove"] = True
        container = docker_client.containers.run(str(image), None, **kwargs)

        # Kill the container on Ctrl+C
        def signal_handler(sig: signal.Signals, frame: types.FrameType) -> None:
            try:
                container.kill()
            except:
                # container.kill() throws if the container has already stopped running
                pass
            finally:
                sys.exit(1)

        signal.signal(signal.SIGINT, signal_handler)

        # container.logs() is blocking, we run it on a separate thread so the SIGINT handler works properly
        # If we run this code on the current thread, SIGINT won't be triggered on Windows when Ctrl+C is triggered
        def print_logs() -> None:
            on_run_called = False

            # Capture all logs and print it to stdout
            for line in container.logs(stream=True, follow=True):
                if not on_run_called:
                    on_run()
                    on_run_called = True

                self._logger.info(line.decode("utf-8").strip())

        thread = threading.Thread(target=print_logs)
        thread.daemon = True
        thread.start()

        while thread.is_alive():
            thread.join(0.1)

        return container.wait()["StatusCode"] == 0

    def build_image(self, dockerfile: Path, target: DockerImage) -> None:
        """Builds a Docker image.

        :param dockerfile: the path to the Dockerfile to build
        :param target: the target name and tag
        """
        # We cannot really use docker_client.images.build() here as it doesn't let us log the progress
        # Building images without showing progress does not provide good developer experience
        # Since the build command is the same on Windows, macOS and Linux we can safely use a system call
        process = subprocess.run(["docker", "build", "-t", str(target), "-f", dockerfile.name, "."],
                                 cwd=dockerfile.parent)

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

    def get_digest(self, image: DockerImage) -> str:
        """Returns the digest of a locally installed image.

        :param image: the image to get the digest of
        :return: the local digest of the image
        """
        img = self._get_docker_client().images.get(str(image))
        return img.attrs["RepoDigests"][0].split("@")[1]

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

    def _get_docker_client(self) -> docker.DockerClient:
        """Creates a DockerClient instance.

        Raises an error if Docker is not running.

        :return: a DockerClient instance which responds to requests
        """
        error = MoreInfoError("Please make sure Docker is installed and running",
                              "https://www.quantconnect.com/docs/v2/lean-cli/user-guides/troubleshooting#02-Common-errors")

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
