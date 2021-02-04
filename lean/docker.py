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
