import os
import re

from setuptools import setup, find_packages

current_dir = os.path.abspath(os.path.dirname(__file__))


def read(relative_path):
    with open(os.path.join(current_dir, relative_path)) as file:
        return file.read()


def get_version():
    version_file = read("lean/__init__.py")
    version_match = re.search(r"^__version__ = \"([^\"]+)\"", version_file, re.M)
    return version_match.group(1)


# Production dependencies
install_requires = [
    "click~=7.1.0",
    "requests~=2.25.0",
    "tqdm~=4.56.0"
]

setup(
    name="lean",
    version=get_version(),
    description="A CLI aimed at making it easier to run QuantConnect's LEAN engine locally and in the cloud",
    author="QuantConnect",
    author_email="support@quantconnect.com",
    url="https://github.com/QuantConnect/lean-cli",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["lean", "lean.*"]),
    entry_points={
        "console_scripts": ["lean=lean.main:main"]
    },
    install_requires=install_requires,
    python_requires=">= 3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9"
    ]
)
