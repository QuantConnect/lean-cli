import itertools
import os
import signal
import sys
import types
from typing import Tuple

import docker

from lean.components.logger import Logger


class DockerManager:
    """The DockerManager contains methods to manage and run Docker images."""

    def __init__(self, logger: Logger) -> None:
        """Creates a new DockerManager instance.

        :param logger: the logger to use when printing messages
        """
        self._logger = logger

    def is_image_installed(self, image: str, tag: str) -> bool:
        """Checks whether a certain image's tag is already installed.

        :param image: the name of the image to check availability for
        :param tag: the image's tag to check availability for
        :return: True if the image has been pulled before, False if not
        """
        docker_client = self._get_docker_client()
        installed_tags = list(itertools.chain(*[x.tags for x in docker_client.images.list()]))
        return f"{image}:{tag}" in installed_tags

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

    def run_image(self, image: str, tag: str, command: str, quiet: bool = False, **kwargs) -> Tuple[bool, str]:
        """Runs a Docker image. If the image is not available yet it will be pulled first.

        See https://docker-py.readthedocs.io/en/stable/containers.html for all the supported kwargs.

        :param image: the name of the image to run
        :param tag: the image's tag to run
        :param command: the command to run
        :param quiet: whether the logs of the image should be printed to stdout
        :param kwargs: the kwargs to forward to docker.containers.run
        :return: whether the command in the container exited successfully and the output of the command
        """
        if not self.is_image_installed(image, tag):
            self.pull_image(image, tag)

        docker_client = self._get_docker_client()

        kwargs["detach"] = True
        container = docker_client.containers.run(f"{image}:{tag}", command, **kwargs)

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

        # Capture all logs and print it to stdout if not running in quiet mode
        output = ""
        for chunk in container.logs(stream=True, follow=True):
            output += chunk.decode("utf-8")
            if not quiet:
                self._logger.info(chunk.decode("utf-8"), newline=False)

        # Flush stdout to make sure messages printed after run_image() appear after the Docker logs
        if not quiet:
            self._logger.flush()

        return container.wait()["StatusCode"] == 0, output

    def _get_docker_client(self) -> docker.DockerClient:
        """Creates a DockerClient instance.

        Raises an error if Docker is not running.

        :return: a DockerClient instance which responds to requests
        """
        error_message = "Please make sure Docker is installed and running"

        try:
            docker_client = docker.from_env()
        except:
            raise RuntimeError(error_message)

        try:
            if not docker_client.ping():
                raise RuntimeError(error_message)
        except:
            raise RuntimeError(error_message)

        return docker_client
