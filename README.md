![LEAN CLI](http://cdn.quantconnect.com.s3.us-east-1.amazonaws.com/i/github/lean-cli-splash.png)
# QuantConnect Lean CLI

[![Build Status](https://github.com/QuantConnect/lean-cli/workflows/Build/badge.svg)](https://github.com/QuantConnect/lean-cli/actions?query=workflow%3ABuild)
[![PyPI Version](https://img.shields.io/pypi/v/lean)](https://pypi.org/project/lean/)
[![Project Status](https://img.shields.io/pypi/status/lean)](https://pypi.org/project/lean/)

**This CLI is still in development. Bugs may still occur and breaking changes may still happen before the first beta release. Use with caution.**

The Lean CLI is a cross-platform CLI aimed at making it easier to develop with the LEAN engine locally and in the cloud.

## Roadmap

The following features are currently planned to be implemented (in order of priority):
- [x] Project scaffolding
- [x] Local autocompletion
- [x] CLI configuration
- [x] Local backtesting
- [x] Local debugging
- [x] Local research environment
- [x] Cloud synchronization
- [x] Cloud backtesting
- [ ] **First beta release**
- [ ] Local data downloading
- [ ] Local optimization
- [ ] Local backtest visualization
- [ ] Local live trading
- [ ] Cloud optimization
- [ ] Cloud live trading
- [ ] Local library support

## Installation

The CLI can be installed and updated by running `pip install -U lean`.

Note that many commands in the CLI require Docker to run. See [Get Docker](https://docs.docker.com/get-docker/) for instructions on how to install Docker for your operating system.

After installing the CLI, simply `cd` into an empty directory and run `lean init` to set up a Lean CLI project. This will scaffold a standard directory structure for you to hit the ground running.

## Usage

A workflow with the CLI may look like this:
1. `cd` into the Lean CLI project.
2. Run `lean create-project "RSI Strategy"` to create a new project with some basic code to get you started.
3. Work on your strategy in `./RSI Strategy`.
4. Run `lean research "RSI Strategy"` to launch a Jupyter Lab session to work on research notebooks. 
5. Run a backtest with `lean backtest "RSI Strategy"`. This runs your backtest in a Docker container containing the same packages as the ones used on QuantConnect.com, but with your own data.

## Debugging backtests

To debug backtests some additional setup is needed depending on the editor and language you use.

*Note: When debugging C#, after you attach to the debugger, a breakpoint will be hit for which your editor will tell you it has no code for. This is expected behavior, simply continue from that breakpoint and your algorithm will start running.*

### VS Code + Python
1. Install the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) extension.
2. Run the `lean backtest` command with the `--debug ptvsd` option.
3. Wait until the CLI tells you to attach to the debugger.
4. In VS Code, open the Run tab and run the configuration called "Debug Python with Lean CLI" (this configuration is created when you run `lean init`).

### VS Code + C#
1. Install version 15.8 of the [Mono Debug](https://marketplace.visualstudio.com/items?itemName=ms-vscode.mono-debug) extension. You can do this by first installing the latest version and then clicking on the arrow button next to the Uninstall button, which will open a context menu containing the "Install Another Version" option.
2. Run the `lean backtest` command with the `--debug mono` option.
3. Wait until the CLI tells you to attach to the debugger.
4. In VS Code, open the Run tab and run the configuration called "Debug C# with Lean CLI" (this configuration is created when you run `lean init`).

### PyCharm + Python
*Note: This combination requires PyCharm Professional.*

1. In PyCharm, start debugging using the "Debug with Lean CLI" run configuration (this configuration is created when you run `lean init`).
2. Run the `lean backtest` command with the `--debug pycharm` option.

### Visual Studio + C#
1. Install the [VSMonoDebugger](https://marketplace.visualstudio.com/items?itemName=GordianDotNet.VSMonoDebugger0d62) extension.
2. In Visual Studio, go to "Extensions > Mono > Settings" and enter the following settings:
    * Remote Host IP: 127.0.0.1
    * Remote Host Port: 55555
    * Mono Debug Port: 55555
3. Run the `lean backtest` command with the `--debug mono` option.
4. Wait until the CLI tells you to attach to the debugger.
5. In Visual Studio, attach to the debugger using "Extensions > Mono > Attach to mono debugger".

### Rider + C#
1. Run the `lean backtest` command with the `--debug mono` option.
2. Wait until the CLI tells you to attach to the debugger.
3. In Rider, start debugging using the "Debug with Lean CLI" run configuration (this configuration is created when you run `lean init`).

## Development

To work on the Lean CLI, clone the repository, enter an environment containing Python 3.6+ and run `pip install -r requirements.txt`. This command will install the required dependencies and installs the CLI in editable mode. This means you'll be able to edit the code and immediately see the results the next time you run `lean`.

If you need to add dependencies, first update `setup.py` (if it is a production dependency) or `requirements.txt` (if it is a development dependency) and then re-run `pip install -r requirements.txt`.

The automated tests can be ran by running `pytest`. The filesystem and HTTP requests are mocked when running tests to make sure they run in an isolated environment.

Maintainers can publish new releases by pushing a Git tag containing the new version to GitHub. This will trigger a GitHub Actions workflow which releases the current `main` branch to PyPI with the value of the tag as version. Make sure the version is not prefixed with "v".
