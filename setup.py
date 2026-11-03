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

import json
import os
import re
import urllib.request

from setuptools import Command, find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

current_dir = os.path.abspath(os.path.dirname(__file__))


def read(relative_path: str) -> str:
    with open(os.path.join(current_dir, relative_path)) as file:
        return file.read()


def get_version() -> str:
    version_file = read("lean/__init__.py")
    version_match = re.search(r"^__version__ = \"([^\"]+)\"", version_file, re.M)
    return version_match.group(1)


def get_stubs_version_range() -> str:
    if "dev" in get_version():
        return ""

    try:
        response = urllib.request.urlopen("https://pypi.org/pypi/quantconnect-stubs/json").read()
        latest_version = json.loads(response)["info"]["version"]
        return f">={latest_version}"
    except:
        return ""


def write_modules_placeholder(command: Command, package_root: str) -> None:
    """Writes an empty placeholder for the modules json the CLI downloads into its package, so pip records the file and
    uninstalling removes it. Only build outputs get it, keeping a checkout's downloaded file intact."""
    # A dry run changes nothing, and an in-place build's package is the checkout itself
    if command.dry_run or os.path.samefile(package_root, current_dir):
        return

    # The name is read rather than imported, as importing lean.models downloads the file
    modules_file_name = re.search(r"^file_name = \"([^\"]+)\"", read("lean/models/__init__.py"), re.M).group(1)
    placeholder_path = os.path.join(package_root, "lean", modules_file_name)

    # Build trees may hard link the checkout's files, so a copied file is replaced rather than truncated
    if os.path.exists(placeholder_path):
        os.remove(placeholder_path)
    with open(placeholder_path, "w"):
        pass


class BuildPyWithModulesPlaceholder(build_py):
    def run(self) -> None:
        super().run()

        # Editable builds link to the checkout, where the downloaded file has to stay
        if getattr(self, "editable_mode", False):
            return

        write_modules_placeholder(self, self.build_lib)


class SdistWithModulesPlaceholder(sdist):
    def make_release_tree(self, base_dir: str, files: list) -> None:
        super().make_release_tree(base_dir, files)
        write_modules_placeholder(self, base_dir)


# Production dependencies
install_requires = [
    "click>=8.0.4",
    "requests>=2.27.1",
    "json5>=0.9.8",
    "docker>=6.0.0",
    "rich>=9.10.0",
    "pydantic>=2.0.0",
    "python-dateutil>=2.8.2",
    "lxml>=4.9.0",
    "joblib>=1.1.0",
    "packaging",
    f"quantconnect-stubs{get_stubs_version_range()}",
    "cryptography>=41.0.4",
    "textual>=1.0.0",
    "plotext>=6.1.0",
]

setup(
    name="lean",
    version=get_version(),
    description="A CLI aimed at making it easier to run QuantConnect's LEAN engine locally and in the cloud",
    author="QuantConnect",
    author_email="support@quantconnect.com",
    url="https://lean.io/cli",
    long_description=read("README.md").replace("](lean", "](https://github.com/QuantConnect/lean-cli/blob/master/lean"),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["lean", "lean.*"]),
    package_data={
        "lean": ["ssh/*"]
    },
    cmdclass={
        "build_py": BuildPyWithModulesPlaceholder,
        "sdist": SdistWithModulesPlaceholder
    },
    entry_points={
        "console_scripts": ["lean=lean.main:main"]
    },
    install_requires=install_requires,
    python_requires=">= 3.9",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14"
    ],
    project_urls={
        "Documentation": "https://www.lean.io/docs/v2/lean-cli/key-concepts/getting-started",
        "Source": "https://github.com/QuantConnect/lean-cli"
    },
)
