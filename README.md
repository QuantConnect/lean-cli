# Lean CLI

[![Build Status](https://github.com/QuantConnect/lean-cli/workflows/Build/badge.svg)](https://github.com/QuantConnect/lean-cli/actions?query=workflow%3ABuild)
[![PyPI Version](https://img.shields.io/pypi/v/lean)](https://pypi.org/project/lean/)

**This CLI is still in development. Bugs may still occur and breaking changes may still happen before the 1.0.0 release. Use with caution.**

The Lean CLI is a CLI aimed at making it easier to run the LEAN engine locally and in the cloud.

## Installation

The CLI can be installed and updated by running `pip install -U lean`.

After installing the CLI, simply `cd` into an empty directory and run `lean init` to set up a Lean CLI project.

## Usage

A workflow with the CLI may look like this:
1. `cd` into the Lean CLI project.
2. Run `lean create-project -l python "RSI Strategy"` to create a new project with some basic code to get you started.
3. Work on your strategy in `./RSI Strategy`.
4. Run a backtest with `lean backtest "RSI Strategy"`. This runs your backtest in a Docker container containing the same packages as the ones used on QuantConnect.com, but with your own data.

## Development

To work on the Lean CLI, clone the repository, enter an environment containing Python 3.6+ and run `pip install -r requirements.txt`. This command will install the required dependencies and installs the CLI in editable mode. This means you'll be able to edit the code and immediately see the results the next time you run `lean`.

If you need to add dependencies, first update `setup.py` (if it is a production dependency) or `requirements.txt` (if it is a development dependency) and then re-run `pip install -r requirements.txt`.

The tests can be ran by running `pytest`. Because a lot of commands interact with the filesystem, the filesystem is mocked before running each test to ensure your local files won't be modified.

Maintainers can publish new releases by pushing a Git tag containing the new version to GitHub. This will trigger a GitHub Actions workflow which releases the current `main` branch to PyPI with the value of the tag as version. Make sure the version is not prefixed with "v".
