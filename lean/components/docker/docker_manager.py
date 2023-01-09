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

from pathlib import Path
from typing import Optional, Set, Any, Dict

from lean.components.util.logger import Logger
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.temp_manager import TempManager
from lean.constants import SITE_PACKAGES_VOLUME_LIMIT, \
    DOCKER_NETWORK, CUSTOM_FOUNDATION, CUSTOM_RESEARCH, CUSTOM_ENGINE

from lean.models.docker import DockerImage
from lean.models.errors import MoreInfoError
from lean.components.util.custom_json_encoder import DecimalEncoder

class DockerManager:
    """The DockerManager contains methods to manage and run Docker images."""

    def __init__(self, logger: Logger, temp_manager: TempManager, platform_manager: PlatformManager) -> None:
        """Creates a new DockerManager instance.

        :param logger: the logger to use when printing messages
        :param temp_manager: the TempManager instance used when creating temporary directories
        :param platform_manager: the PlatformManager used when checking which operating system is in use
        """
        self._logger = logger
        self._temp_manager = temp_manager
        self._platform_manager = platform_manager

    def pull_image(self, image: DockerImage) -> None:
        """Pulls a Docker image.

        :param image: the image to pull
        """
        from shutil import which
        from subprocess import run

        if image.name == CUSTOM_RESEARCH or image.name == CUSTOM_ENGINE or image.name == CUSTOM_FOUNDATION:
            self._logger.info(f"Skip pulling local image {image}...")
            return

        self._logger.info(f"Pulling {image}...")
        # We cannot really use docker_client.images.pull() here as it doesn't let us log the progress
        # Downloading multiple gigabytes without showing progress does not provide good developer experience
        # Since the pull command is the same on Windows, macOS and Linux we can safely use a system call
        if which("docker") is not None:
            process = run(["docker", "image", "pull", str(image)])
            if process.returncode != 0:
                raise RuntimeError(
                    f"Something went wrong while pulling {image}, see the logs above for more information")
        else:
            self._get_docker_client().images.pull(image.name, image.tag)

    def run_image(self, image: DockerImage, **kwargs) -> bool:
        """Runs a Docker image. If the image is not available locally it will be pulled first.

        See https://docker-py.readthedocs.io/en/stable/containers.html for all the supported kwargs.

        If kwargs contains an "on_output" property, it is removed before passing it on to docker.containers.run
        and the given lambda is ran whenever the Docker container prints anything.

        If kwargs contains an "format_output" property, it is removed before passing it on to docker.containers.run
        and the given lambda is ran after the Docker container completes running.

        If kwargs contains a "commands" property, it is removed before passing it on to docker.containers.run
        and the Docker container is configured to run the given commands.
        This property causes the "entrypoint" property to be overwritten if it exists.

        If kwargs sets "detach" to True, the method returns as soon as the container starts.
        If this is not the case, the method is blocking and runs until the container exits.

        :param image: the image to run
        :param kwargs: the kwargs to forward to docker.containers.run
        :return: True if the command in the container exited successfully, False if not
        """
        from signal import signal, SIGINT, Signals
        from platform import node
        from sys import stdout, exit
        from threading import Thread
        from types import FrameType
        from docker.errors import APIError
        from docker.types import Mount

        if not self.image_installed(image):
            self.pull_image(image)

        on_output = kwargs.pop("on_output", lambda chunk: None)
        format_output = kwargs.pop("format_output", lambda chunk: None)
        commands = kwargs.pop("commands", None)

        if commands is not None:
            shell_script_commands = ["#!/usr/bin/env bash", "set -e"]
            if self._logger.debug_logging_enabled:
                shell_script_commands.append("set -x")
            shell_script_commands += commands

            shell_script_path = self._temp_manager.create_temporary_directory() / "lean-cli-start.sh"
            with shell_script_path.open("w+", encoding="utf-8", newline="\n") as file:
                file.write("\n".join(shell_script_commands) + "\n")

            if "mounts" not in kwargs:
                kwargs["mounts"] = []

            kwargs["mounts"].append(Mount(target="/lean-cli-start.sh",
                                          source=str(shell_script_path),
                                          type="bind",
                                          read_only=True))
            kwargs["entrypoint"] = ["bash", "/lean-cli-start.sh"]

        # Format all source paths
        if "mounts" in kwargs:
            for mount in kwargs["mounts"]:
                mount["Source"] = self._format_source_path(mount["Source"])

        if "volumes" in kwargs:
            for key in list(kwargs["volumes"].keys()):
                new_key = self._format_source_path(key)
                kwargs["volumes"][new_key] = kwargs["volumes"].pop(key)

        detach = kwargs.pop("detach", False)
        is_tty = stdout.isatty()

        kwargs["detach"] = True
        kwargs["hostname"] = kwargs["hostname"] if "hostname" in kwargs else node()
        kwargs["tty"] = is_tty and not detach
        kwargs["stdin_open"] = is_tty and not detach
        kwargs["stop_signal"] = kwargs.get("stop_signal", "SIGKILL")

        if detach and "remove" not in kwargs:
            kwargs["remove"] = True

        # Make sure host.docker.internal resolves on Linux
        # See https://github.com/QuantConnect/Lean/pull/5092
        if self._platform_manager.is_host_linux():
            if "extra_hosts" not in kwargs:
                kwargs["extra_hosts"] = {}
            kwargs["extra_hosts"]["host.docker.internal"] = "172.17.0.1"

        # Run all containers on a custom bridge network
        # This makes it possible for containers to connect to each other by name
        self.create_network(DOCKER_NETWORK)
        kwargs["network"] = DOCKER_NETWORK

        # Remove existing image with the same name if it exists and is not running
        if "name" in kwargs:
            existing_container = self.get_container_by_name(kwargs["name"])
            if existing_container is not None and existing_container.status != "running":
                existing_container.remove()

        self._logger.debug(f"Running '{image}' with the following configuration:")
        self._logger.debug(kwargs)

        docker_client = self._get_docker_client()
        container = docker_client.containers.run(str(image), None, **kwargs)

        if detach:
            return True

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
                exit(1)

        # Kill the container on Ctrl+C
        def signal_handler(sig: Signals, frame: FrameType) -> None:
            nonlocal force_kill_next
            if not is_tty or force_kill_next or kwargs["stop_signal"] == "SIGKILL":
                force_kill_current = True
            else:
                self._logger.info("Waiting 1 minute for LEAN to exit gracefully, press Ctrl+C again to force stop")
                force_kill_next = True
                force_kill_current = False

            # If we run this code on the current thread, a second Ctrl+C won't be detected on Windows
            kill_thread = Thread(target=kill_container, args=[force_kill_current])
            kill_thread.daemon = True
            kill_thread.start()

        signal(SIGINT, signal_handler)

        # container.logs() is blocking, we run it on a separate thread so the SIGINT handler works properly
        # If we run this code on the current thread, SIGINT won't be triggered on Windows when Ctrl+C is triggered
        def print_logs() -> None:
            chunk_buffer = bytes()
            is_first_time = True
            log_dump = ""

            try:
                while True:
                    container.reload()
                    if container.status != "running":
                        return log_dump

                    if is_first_time:
                        tail = "all"
                        is_first_time = False
                    else:
                        tail = 0

                    # Capture all logs and print it to stdout line by line
                    for chunk in container.logs(stream=True, follow=True, tail=tail):
                        chunk_buffer += chunk

                        if not chunk_buffer.endswith(b"\n"):
                            continue

                        chunk = chunk_buffer.decode("utf-8")
                        chunk_buffer = bytes()

                        if on_output is not None:
                            on_output(chunk)

                        log_dump = log_dump + chunk
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
            except:
                # This will crash when the container exits, ignore the exception
                pass

        def print_and_format_logs():
            log_dump = print_logs()
            if format_output is not None:
                format_output(log_dump)

        logs_thread = Thread(target=print_and_format_logs)
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
                exit(1)

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
        from subprocess import run
        # We cannot really use docker_client.images.build() here as it doesn't let us log the progress
        # Building images without showing progress does not provide good developer experience
        # Since the build command is the same on Windows, macOS and Linux we can safely use a system call
        process = run(["docker", "build", "-t", str(target), "-f", str(dockerfile), "."], cwd=root)

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

    def get_local_digest(self, image: DockerImage) -> Optional[str]:
        """Returns the digest of a locally installed image.

        :param image: the local image to get the digest of
        :return: the digest of the local image, or None if the digest does not exist
        """
        img = self._get_docker_client().images.get(str(image))

        repo_digests = img.attrs["RepoDigests"]
        if len(repo_digests) == 0:
            return None

        return repo_digests[0].split("@")[1]

    def get_remote_digest(self, image: DockerImage) -> str:
        """Returns the digest of a remote image.

        :param image: the remote image to get the digest of
        :return: the digest of the remote image
        """
        img = self._get_docker_client().images.get_registry_data(str(image))
        return img.attrs["Descriptor"]["digest"]

    def create_network(self, name: str) -> None:
        """Creates a new bridge network, or does nothing if a network with the given name already exists.

        :param name: the name of then network to create
        """
        docker_client = self._get_docker_client()
        if not any(n.name == name for n in docker_client.networks.list()):
            docker_client.networks.create(name, driver="bridge")

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
        from hashlib import md5
        from dateutil.parser import isoparse

        requirements_hash = md5(requirements_file.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
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

    def get_running_containers(self) -> Set[str]:
        """Returns the names of all running containers.

        :return: a set containing the names of all running Docker containers
        """
        containers = self._get_docker_client().containers.list()
        return {c.name.lstrip("/") for c in containers if c.status == "running"}

    def get_container_by_name(self, container_name: str):
        """Finds a container with a given name.

        :param container_name: the name of the container to find
        :return: the container with the given name, or None if it does not exist
        """
        for container in self._get_docker_client().containers.list(all=True):
            if container.name.lstrip("/") == container_name:
                return container

        return None

    def show_logs(self, container_name: str, follow: bool = False) -> None:
        """Shows the logs of a Docker container in the terminal.

        :param container_name: the name of the container to show the logs of
        :param follow: whether the logs should be streamed in real-time if the container is running (defaults to False)
        """
        from subprocess import run
        if self.get_container_by_name(container_name) is None:
            return

        # We cannot use the Docker Python SDK to get live logs consistently
        # Since the logs command is the same on Windows, macOS and Linux we can safely use a system call
        command = ["docker", "logs"]
        if follow:
            command.append("-f")
        command.append(container_name)

        run(command)

    def is_missing_permission(self) -> bool:
        """Returns whether we cannot connect to the Docker client because of a permissions issue.

        A permissions issue usually indicates that the client can only be used with root privileges.

        :return: True if we cannot connect to the Docker client because of a permissions issue, False if that's not
        """
        try:
            from docker import from_env
            from_env()
        except Exception as exception:
            return "Permission denied" in str(exception)
        return False

    def write_to_file(self, docker_container_name: str, docker_file: Path, data: Dict[str, Any]) -> None:
        """Write data to the file in docker.

        Args:
            docker_container_name: The name of the container to write to
            docker_file: The Dockerfile to write to.
            data: The data to write to the Dockerfile.
        """
        from subprocess import run, CalledProcessError
        from json import dumps

        docker_container = self.get_container_by_name(docker_container_name)
        if docker_container is None:
            raise ValueError(f"Container {docker_container_name} does not exist")
        if docker_container.status != "running":
            raise ValueError(f"Container {docker_container_name} is not running")

        data = dumps(data, cls=DecimalEncoder)
        data = data.replace('"','\\"')
        command = f'docker exec {docker_container_name} bash -c "echo \'{data}\' > {docker_file.as_posix()}"'
        try:
            run(command, shell=True, check=True)
        except CalledProcessError as exception:
            raise ValueError(f"Failed to write to {docker_file.name}: {exception.output.decode('utf-8')}")
        except Exception as e:
            raise ValueError(f"Failed to write to {docker_file.name}: {e}")

    def read_from_file(self, docker_container_name: str, docker_file: Path, interval=1, timeout=30) -> Dict[str,Any]:
        """Read data from file in docker.

        Args:
            docker_container_name: The name of the container to write to
            docker_file: The Dockerfile to write to.
            interval: The interval to sleep before checking again.
            timeout: The timeout to wait for the file.
        """
        from json import loads
        from subprocess import Popen, PIPE, CalledProcessError
        from time import sleep, time

        command = f'docker exec {docker_container_name} bash -c "cat {docker_file.as_posix()}"'
        start = time()
        success = False
        error_message = None
        container_running = True
        while time() - start < timeout:
            try:
                docker_container = self.get_container_by_name(docker_container_name)
                if docker_container is None:
                    error_message = f"Container {docker_container_name} does not exist"
                    container_running = False
                    break
                p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
                output = p.stdout.read().decode('utf-8')
                if output is not None and output != "":
                    success = True
                    break
            except CalledProcessError as exception:
                error_message = f"Failed to read result from docker file {docker_file.name}: {exception.output.decode('utf-8')} {p.stderr.read().decode('utf-8')}"
                sleep(interval)
            except Exception as e:
                error_message = f"Failed to read result from docker file {docker_file.name}: {e} {p.stderr.read().decode('utf-8')}"
                sleep(interval)

        if success:
            result = loads(output)
            success = result["Success"]
            if not success:
                error_message = "Rejected by Lean. Possible arguments error. Please check your logs and try again."
        if not success and not error_message:
            error_message = f"Failed to read result from docker file {docker_file.name} within {timeout} seconds"

        return {
            "error": error_message,
            "success": success,
            "container-running": container_running
        }


    def _get_docker_client(self):
        """Creates a DockerClient instance.

        Raises an error if Docker is not running.

        :return: a DockerClient instance which responds to requests
        """
        error = MoreInfoError("Please make sure Docker is installed and running",
                              "https://www.lean.io/docs/v2/lean-cli/key-concepts/troubleshooting#02-Common-Errors")

        try:
            from docker import from_env
            docker_client = from_env()
        except Exception:
            raise error

        try:
            if not docker_client.ping():
                raise error
        except Exception:
            raise error

        return docker_client

    def _format_source_path(self, path: str) -> str:
        """Formats a source path so Docker knows what it refers to.

        This method does two things:
        1. If Docker Toolbox is in use, it converts paths like C:/Path to /c/Path.
        2. If Docker is running in Docker, it converts paths to the corresponding paths on the host system.

        :param path: the original path
        :return: the original path formatted in such a way that Docker can understand it
        """
        from os import environ
        from json import loads

        # Docker Toolbox modifications
        is_windows = self._platform_manager.is_system_windows()
        is_docker_toolbox = "machine/machines" in environ.get("DOCKER_CERT_PATH", "").replace("\\", "/")
        if is_windows and is_docker_toolbox:
            # Backward slashes to forward slashes
            path = path.replace('\\', '/')

            # C:/Path to /c/Path
            path = f"/{path[0].lower()}/{path[3:]}"

        # Docker in Docker modifications
        path_mappings = loads(environ.get("DOCKER_PATH_MAPPINGS", "{}"))
        for container_path, host_path in path_mappings.items():
            if path.startswith(container_path):
                path = host_path + path[len(container_path):]
                break

        return path
