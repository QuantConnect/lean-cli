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

import os
import platform


class PlatformManager:
    """The PlatformManager class makes it easy to detect which platform the user is using."""

    def __init__(self) -> None:
        """Creates a new PlatformManager instance."""
        self._system = platform.system()
        self._machine = platform.machine()
        self._host_system = os.environ.get("QC_DOCKER_HOST_SYSTEM", None)
        self._host_machine = os.environ.get("QC_DOCKER_HOST_MACHINE", None)

    def is_system_windows(self) -> bool:
        """Returns whether the current system is running Windows.

        If this method is called inside Docker, it returns whether the Docker container is running Windows.

        :return: whether the current system is running Windows
        """
        return self._system == "Windows"

    def is_system_macos(self) -> bool:
        """Returns whether the current system is running macOS.

        If this method is called inside Docker, it returns whether the Docker container is running macOS.

        :return: whether the current system is running macOS
        """
        return self._system == "Darwin"

    def is_system_linux(self) -> bool:
        """Returns whether the current system is running Linux.

        If this method is called inside Docker, it returns whether the Docker container is running Linux.

        :return: whether the current system is running Linux
        """
        return self._system == "Linux"

    def is_system_arm(self) -> bool:
        """Returns whether the current system is running on the ARM architecture.

        If this method is called inside Docker, it returns whether the Docker container is running on ARM.

        :return: whether the current system is running on ARM
        """
        return self._machine in ["arm64", "aarch64"]

    def is_host_windows(self) -> bool:
        """Returns whether the current host is running Windows.

        If this method is called outside Docker, it behaves identical to is_system_windows().
        If this method is called inside Docker, it returns whether the Docker host is running Windows.

        :return: whether the current host is running Windows
        """
        if self._host_system is None:
            return self.is_system_windows()
        return self._host_system == "Windows"

    def is_host_macos(self) -> bool:
        """Returns whether the current host is running macOS.

        If this method is called outside Docker, it behaves identical to is_system_macos().
        If this method is called inside Docker, it returns whether the Docker host is running macOS.

        :return: whether the current host is running macOS
        """
        if self._host_system is None:
            return self.is_system_macos()
        return self._host_system == "Darwin"

    def is_host_linux(self) -> bool:
        """Returns whether the current host is running Linux.

        If this method is called outside Docker, it behaves identical to is_system_linux().
        If this method is called inside Docker, it returns whether the Docker host is running Linux.

        :return: whether the current host is running Linux
        """
        if self._host_system is None:
            return self.is_system_linux()
        return self._host_system == "Linux"

    def is_host_arm(self) -> bool:
        """Returns whether the current host is running on the ARM architecture.

        If this method is called outside Docker, it behaves identical to is_system_arm().
        If this method is called inside Docker, it returns whether the Docker host is running on ARM.

        :return: whether the current host is running on ARM
        """
        if self._host_machine is None:
            return self.is_system_arm()
        return self._host_machine in ["arm64", "aarch64"]
