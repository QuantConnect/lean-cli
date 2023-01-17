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

from setuptools import find_packages, setup

current_dir = os.path.abspath(os.path.dirname(__file__))


def read(relative_path: str) -> str:
    with open(os.path.join(current_dir, relative_path)) as file:
        return file.read()


def get_version() -> str:
    version_file = read("lean/__init__.py")
    version_match = re.search(r"^__version__ = \"([^\"]+)\"", version_file, re.M)
    return version_match.group(1)


def get_stubs_version_range() -> str:
    if get_version() == "dev":
        return ""

    try:
        response = urllib.request.urlopen("https://pypi.org/pypi/quantconnect-stubs/json").read()
        latest_version = json.loads(response)["info"]["version"]
        return f">={latest_version}"
    except:
        return ""


# Production dependencies
install_requires = [
    "click>=8.0.4",
    "requests>=2.27.1",
    "json5>=0.9.8",
    "docker>=6.0.0",
    "rich>=9.10.0",
    "pydantic>=1.8.2",
    "python-dateutil>=2.8.2",
    "lxml>=4.9.0",
    "maskpass>=0.3.6",
    "joblib>=1.1.0",
    "wrapt~=1.14.1",
    "setuptools",
    f"quantconnect-stubs{get_stubs_version_range()}"
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
    entry_points={
        "console_scripts": ["lean=lean.main:main"]
    },
    install_requires=install_requires,
    python_requires=">= 3.7",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10"
    ],
    project_urls={
        "Documentation": "https://www.lean.io/docs/v2/lean-cli/key-concepts/getting-started",
        "Source": "https://github.com/QuantConnect/lean-cli"
    },
)
