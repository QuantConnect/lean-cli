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

import itertools
import os
import signal
import sys
import threading
import types

import docker
import requests

from lean.components.util.logger import Logger


class DockerManager:
    """The DockerManager contains methods to manage and run Docker images."""

    def __init__(self, logger: Logger) -> None:
        """Creates a new DockerManager instance.

        :param logger: the logger to use when printing messages
        """
        self._logger = logger

    def pull_image(self, image: str, tag: str) -> None:
        """Pulls a Docker image.

        :param image: the name of the image to pull
        :param tag: the image's tag to pull
        """
        self._logger.info(f"Pulling {image}:{tag}, this may take a while...")

        # We cannot really use docker_client.images.pull() here as it doesn't let us log the progress
        # Downloading multiple gigabytes without showing progress does not provide good developer experience
        # Since the pull command is the same on Windows, Linux and macOS we can safely use a system call
        os.system(f"docker image pull {image}:{tag}")

    def run_image(self, image: str, tag: str, **kwargs) -> bool:
        """Runs a Docker image. If the image is not available yet it will be pulled first.

        See https://docker-py.readthedocs.io/en/stable/containers.html for all the supported kwargs.

        If kwargs contains an "on_run" property, it is removed before passing it on to docker.containers.run
        and the given lambda is ran when the Docker container has started.

        :param image: the name of the image to run
        :param tag: the image's tag to run
        :param kwargs: the kwargs to forward to docker.containers.run
        :return: True if the command in the container exited successfully, False if not
        """
        if not self.tag_installed(image, tag):
            self.pull_image(image, tag)

        on_run = kwargs.pop("on_run", lambda: None)

        docker_client = self._get_docker_client()

        kwargs["detach"] = True
        container = docker_client.containers.run(f"{image}:{tag}", None, **kwargs)

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
        # If we run this code on the current thread, SIGINT won't be triggered on Windows for some reason
        def print_logs() -> None:
            on_run_called = False

            # Capture all logs and print it to stdout if not running in quiet mode
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

    def tag_installed(self, image: str, tag: str) -> bool:
        """Returns whether a certain image's tag is installed.

        :param image: the name of the image to check availability for
        :param tag: the image's tag to check availability for
        :return: True if the image's tag has been pulled before, False if not
        """
        docker_client = self._get_docker_client()
        installed_tags = list(itertools.chain(*[x.tags for x in docker_client.images.list()]))
        return f"{image}:{tag}" in installed_tags

    def tag_exists(self, image: str, tag: str) -> bool:
        """Returns whether a certain tag exists for a certain image in the Docker registry.

        :param image: the image to check the tag of
        :param tag: the tag to check the existence of
        :return: True if the tag exists for the given image on the Docker Registry, False if not
        """
        tags_list = requests.get(f"https://registry.hub.docker.com/v1/repositories/{image}/tags").json()
        return any([x["name"] == tag for x in tags_list])

    def get_tag_digest(self, image: str, tag: str) -> str:
        """Returns the digest of a locally installed image's tag.

        :param image: the image to get the digest of a tag of
        :param tag: the image's tag to get the digest of
        :return: the local digest of the image's tag
        """
        image = self._get_docker_client().images.get(f"{image}:{tag}")
        return image.attrs["RepoDigests"][0].split("@")[1]

    def _get_docker_client(self) -> docker.DockerClient:
        """Creates a DockerClient instance.

        Raises an error if Docker is not running.

        :return: a DockerClient instance which responds to requests
        """
        error_message = "Please make sure Docker is installed and running"

        try:
            docker_client = docker.from_env()
        except Exception:
            raise RuntimeError(error_message)

        try:
            if not docker_client.ping():
                raise RuntimeError(error_message)
        except Exception:
            raise RuntimeError(error_message)

        return docker_client
