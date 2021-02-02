# Lean CLI

[![Build Status](https://github.com/QuantConnect/lean-cli/workflows/Build/badge.svg)](https://github.com/QuantConnect/lean-cli/actions?query=workflow%3ABuild)
[![PyPI Version](https://img.shields.io/pypi/v/lean)](https://pypi.org/project/lean/)

The Lean CLI is a CLI aimed at making it easier to run the LEAN engine locally and in the cloud.

## Installation

In the future: `pip install -U lean`.

Usage instructions will be added when there is something usable in this repository.

## Development

To work on the Lean CLI, clone the repository, enter an environment containing Python 3.6+ and run `pip install -r requirements.txt`. This command will install the required dependencies and installs the CLI in editable mode. This means you'll be able to edit the code and immediately see the results the next time you run `lean`.

If you need to add dependencies, first update `setup.py` (if it is a production dependency) or `requirements.txt` (if it is a development dependency) and re-run `pip install -r requirements.txt`.

The unit tests can be ran by running `pytest`.
