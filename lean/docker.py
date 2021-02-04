import itertools
import os

import click
import docker


def get_docker_client() -> docker.DockerClient:
    """Create a DockerClient instance, abort execution if Docker is not available."""
    docker_client = docker.from_env()
    docker_available = True

    try:
        if not docker_client.ping():
            docker_available = False
    except:
        docker_available = False

    if not docker_available:
        raise click.ClickException("Please make sure Docker is installed and running")

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


def run_image(image: str, tag: str, command: str, **kwargs) -> bool:
    """
    Run a Docker image. If the image is not available yet it will be pulled first.

    See https://docker-py.readthedocs.io/en/stable/containers.html for all the supported kwargs.

    :param image: the name of the image to run
    :param tag: the image's tag to run
    :param command: the command to run
    :param kwargs: the kwargs to forward to docker.containers.run
    :return: True if the command in the container exited successfully, False if not
    """
    if not is_image_available(image, tag):
        pull_image(image, tag)

    docker_client = get_docker_client()

    container = docker_client.containers.run(f"{image}:{tag}", command, **kwargs)
    for line in container.logs(stream=True, follow=True):
        click.echo(line, nl=False)

    return container.wait()["StatusCode"] == 0
