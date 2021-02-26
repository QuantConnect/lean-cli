![Lean CLI](http://cdn.quantconnect.com.s3.us-east-1.amazonaws.com/i/github/lean-cli-splash.png)

# QuantConnect Lean CLI

[![Build Status](https://github.com/QuantConnect/lean-cli/workflows/Build/badge.svg)](https://github.com/QuantConnect/lean-cli/actions?query=workflow%3ABuild)
[![PyPI Version](https://img.shields.io/pypi/v/lean)](https://pypi.org/project/lean/)
[![Project Status](https://img.shields.io/pypi/status/lean)](https://pypi.org/project/lean/)

**This CLI is still in development. Bugs may still occur and breaking changes may still happen before the first beta release. Use with caution.**

The Lean CLI is a cross-platform CLI aimed at making it easier to develop with the LEAN engine locally and in the cloud.

## Table of Contents

- [Roadmap](#roadmap)
- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)
- [Local debugging](#local-debugging)
- [Development](#development)

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

The Lean CLI supports multiple workflows. The examples below serve as a starting point, you're free to mix local and cloud features in any way you'd like.

A locally-focused workflow (local development, local execution) with the CLI may look like this:
1. `cd` into the Lean CLI project.
2. Run `lean create-project "RSI Strategy"` to create a new project with some basic code to get you started.
3. Work on your strategy in `./RSI Strategy`.
4. Run `lean research "RSI Strategy"` to launch a Jupyter Lab session to work on research notebooks. 
5. Run a backtest with `lean backtest "RSI Strategy"`. This runs your backtest in a Docker container containing the same packages as the ones used on QuantConnect.com, but with your own data.

A cloud-focused workflow (local development, cloud execution) with the CLI may look like this:
1. `cd` into the Lean CLI project.
2. Run `lean cloud pull` to pull remotely changed files.
3. Start programming locally and run backtests in the cloud with `lean cloud backtest "Project Name" --open --push` whenever there is something to backtest. The `--open` flag means that the backtest results will be opened in the browser when done, while the `--push` flag means that local changes are pushed to the cloud before running the backtest.
4. Whenever you need to create a new project, run `lean create-project "Project Name"` and `lean cloud push --project "Project Name"` to create a new project containing some basic code and to push it to the cloud.
5. When you're done for the moment, run `lean cloud push` to push all locally changed files to the cloud.

## Commands

<!-- commands start -->
- [`lean backtest`](#lean-backtest)
- [`lean cloud backtest`](#lean-cloud-backtest)
- [`lean cloud pull`](#lean-cloud-pull)
- [`lean cloud push`](#lean-cloud-push)
- [`lean config get`](#lean-config-get)
- [`lean config list`](#lean-config-list)
- [`lean config set`](#lean-config-set)
- [`lean create-project`](#lean-create-project)
- [`lean init`](#lean-init)
- [`lean login`](#lean-login)
- [`lean logout`](#lean-logout)
- [`lean research`](#lean-research)

### `lean backtest`

Backtest a project locally using Docker.

```
Usage: lean backtest [OPTIONS] PROJECT

  Backtest a project locally using Docker.

  If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
  If PROJECT is a file, the algorithm in the specified file will be executed.

  Go to the following url to learn how to debug backtests locally using the Lean CLI:
  https://github.com/QuantConnect/lean-cli#local-debugging

Options:
  --output DIRECTORY            Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP)
  --debug [pycharm|ptvsd|mono]  Enable a certain debugging method (see --help for more information)
  --update                      Pull the selected LEAN engine version before running the backtest
  --version TEXT                The LEAN engine version to run (defaults to the latest installed version)
  --help                        Show this message and exit.
  --lean-config FILE            The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                     Enable debug logging
```

_See code: [lean/commands/backtest.py](lean/commands/backtest.py)_

### `lean cloud backtest`

Run a backtest in the cloud.

```
Usage: lean cloud backtest [OPTIONS] PROJECT

  Run a backtest in the cloud.

  PROJECT should be the name or id of a cloud project.

  If the project that has to be backtested has been pulled to the local drive with `lean cloud pull` it is possible to
  use the --push option to push local modifications to the cloud before running the backtest.

Options:
  --name TEXT  The name of the backtest (a random one is generated if not specified)
  --push       Push local modifications to the cloud before running the backtest
  --open       Automatically open the browser with the results when the backtest is finished
  --help       Show this message and exit.
  --verbose    Enable debug logging
```

_See code: [lean/commands/cloud/backtest.py](lean/commands/cloud/backtest.py)_

### `lean cloud pull`

Pull projects from QuantConnect to the local drive.

```
Usage: lean cloud pull [OPTIONS]

  Pull projects from QuantConnect to the local drive.

  This command overrides the content of local files with the content of their respective counterparts in the cloud.

  This command will not delete local files for which there is no counterpart in the cloud.

Options:
  --project TEXT   Name or id of the project to pull (all cloud projects if not specified)
  --pull-bootcamp  Pull Boot Camp projects (disabled by default)
  --help           Show this message and exit.
  --verbose        Enable debug logging
```

_See code: [lean/commands/cloud/pull.py](lean/commands/cloud/pull.py)_

### `lean cloud push`

Push local projects to QuantConnect.

```
Usage: lean cloud push [OPTIONS]

  Push local projects to QuantConnect.

  This command overrides the content of cloud files with the content of their respective local counterparts.

  This command will not delete cloud files which don't have a local counterpart.

Options:
  --project DIRECTORY  Path to the local project to push (all local projects if not specified)
  --help               Show this message and exit.
  --verbose            Enable debug logging
```

_See code: [lean/commands/cloud/push.py](lean/commands/cloud/push.py)_

### `lean config get`

Get the current value of a configurable option.

```
Usage: lean config get [OPTIONS] KEY

  Get the current value of a configurable option.

  Sensitive options like credentials cannot be retrieved this way for security reasons. Please open
  ~/.lean/credentials if you want to see your currently stored credentials.

  Run `lean config list` to show all available options.

Options:
  --help     Show this message and exit.
  --verbose  Enable debug logging
```

_See code: [lean/commands/config/get.py](lean/commands/config/get.py)_

### `lean config list`

List the configurable options and their current values.

```
Usage: lean config list [OPTIONS]

  List the configurable options and their current values.

Options:
  --help     Show this message and exit.
  --verbose  Enable debug logging
```

_See code: [lean/commands/config/list.py](lean/commands/config/list.py)_

### `lean config set`

Set a configurable option.

```
Usage: lean config set [OPTIONS] KEY VALUE

  Set a configurable option.

  Run `lean config list` to show all available options.

Options:
  --help     Show this message and exit.
  --verbose  Enable debug logging
```

_See code: [lean/commands/config/set.py](lean/commands/config/set.py)_

### `lean create-project`

Create a new project containing starter code.

```
Usage: lean create-project [OPTIONS] NAME

  Create a new project containing starter code.

  If NAME is a path containing subdirectories those will be created automatically.

  The default language can be set using `lean config set default-language python/csharp`.

Options:
  -l, --language [python|csharp]  The language of the project to create
  --help                          Show this message and exit.
  --verbose                       Enable debug logging
```

_See code: [lean/commands/create_project.py](lean/commands/create_project.py)_

### `lean init`

Bootstrap a Lean CLI project.

```
Usage: lean init [OPTIONS]

  Bootstrap a Lean CLI project.

Options:
  --help     Show this message and exit.
  --verbose  Enable debug logging
```

_See code: [lean/commands/init.py](lean/commands/init.py)_

### `lean login`

Log in with a QuantConnect account.

```
Usage: lean login [OPTIONS]

  Log in with a QuantConnect account.

  If user id or API token is not provided an interactive prompt will show.

  Credentials are stored in ~/.lean/credentials and are removed upon running `lean logout`.

Options:
  -u, --user-id TEXT    QuantConnect.com user id
  -t, --api-token TEXT  QuantConnect.com API token
  --help                Show this message and exit.
  --verbose             Enable debug logging
```

_See code: [lean/commands/login.py](lean/commands/login.py)_

### `lean logout`

Log out and remove stored credentials.

```
Usage: lean logout [OPTIONS]

  Log out and remove stored credentials.

Options:
  --help     Show this message and exit.
  --verbose  Enable debug logging
```

_See code: [lean/commands/logout.py](lean/commands/logout.py)_

### `lean research`

Run a Jupyter Lab environment locally using Docker.

```
Usage: lean research [OPTIONS] PROJECT

  Run a Jupyter Lab environment locally using Docker.

Options:
  --port INTEGER      The port to run Jupyter Lab on (defaults to 8888)
  --update            Pull the selected research environment version before starting it
  --version TEXT      The version of the research environment version to run (defaults to the latest installed version)
  --help              Show this message and exit.
  --lean-config FILE  The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose           Enable debug logging
```

_See code: [lean/commands/research.py](lean/commands/research.py)_
<!-- commands end -->

## Local debugging

To debug backtests locally some additional setup is needed depending on the editor and language you use.

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

To update the commands reference part of the readme run `python scripts/readme.py` from the root of the project.

Maintainers can publish new releases by pushing a Git tag containing the new version to GitHub. This will trigger a GitHub Actions workflow which releases the current `main` branch to PyPI with the value of the tag as version. Make sure the version is not prefixed with "v".
