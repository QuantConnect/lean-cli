import itertools
import os
import signal
import sys
import types
from typing import Tuple

import click
import docker


def get_docker_client() -> docker.DockerClient:
    """Create a DockerClient instance, abort execution if Docker is not available."""
    error_message = "Please make sure Docker is installed and running"

    try:
        docker_client = docker.from_env()
    except:
        raise click.ClickException(error_message)

    try:
        if not docker_client.ping():
            raise click.ClickException(error_message)
    except:
        raise click.ClickException(error_message)

    return docker_client


def is_image_available(image: str, tag: str) -> bool:
    """Check whether a certain image's tag has been downloaded before.

    :param image: the name of the image to check availability for
    :param tag: the image's tag to check availability for
    :return: True if the image has been pulled before, False if not
    """
    docker_client = get_docker_client()
    installed_tags = list(itertools.chain(*[x.tags for x in docker_client.images.list()]))
    return f"{image}:{tag}" in installed_tags


def pull_image(image: str, tag: str) -> None:
    """Pull a Docker image.

    :param image: the name of the image to pull
    :param tag: the image's tag to pull
    """
    click.echo(f"Pulling {image}:{tag}, this may take a while...")

    # We cannot really use docker_client.images.pull() here as it doesn't let us log the progress
    # Downloading multiple gigabytes without showing progress does not provide good developer experience
    # Since the pull command is the same on Windows, Linux and macOS we can safely use a system call
    os.system(f"docker image pull {image}:{tag}")


def run_image(image: str, tag: str, command: str, quiet: bool, **kwargs) -> Tuple[bool, str]:
    """
    Run a Docker image. If the image is not available yet it will be pulled first.

    See https://docker-py.readthedocs.io/en/stable/containers.html for all the supported kwargs.

    :param image: the name of the image to run
    :param tag: the image's tag to run
    :param command: the command to run
    :param quiet: whether the logs of the image should be printed to stdout
    :param kwargs: the kwargs to forward to docker.containers.run
    :return: a tuple containing whether the command in the container exited successfully and the output of the command
    """
    if not is_image_available(image, tag):
        pull_image(image, tag)

    docker_client = get_docker_client()

    kwargs["detach"] = True
    container = docker_client.containers.run(f"{image}:{tag}", command, **kwargs)

    # Kill the container on Ctrl+C
    def signal_handler(sig: signal.Signals, frame: types.FrameType) -> None:
        try:
            container.kill()
        except:
            # container.kill() throws if the container has already stopped running
            pass

        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    # Capture all logs and print it to stdout if not running in quiet mode
    output = ""
    for chunk in container.logs(stream=True, follow=True):
        output += chunk.decode("utf-8")
        if not quiet:
            click.echo(chunk, nl=False)

    # Flush stdout to make sure messages printed after run_image() appear after the Docker logs
    if not quiet:
        sys.stdout.flush()

    return container.wait()["StatusCode"] == 0, output
