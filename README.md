![Lean CLI](http://cdn.quantconnect.com.s3.us-east-1.amazonaws.com/i/github/lean-cli-splash.png)

# QuantConnect Lean CLI

[![Build Status](https://github.com/QuantConnect/lean-cli/workflows/Build/badge.svg)](https://github.com/QuantConnect/lean-cli/actions?query=workflow%3ABuild)
[![PyPI Version](https://img.shields.io/pypi/v/lean)](https://pypi.org/project/lean/)
[![Project Status](https://img.shields.io/pypi/status/lean)](https://pypi.org/project/lean/)

**This CLI is still in development. Bugs may still occur and breaking changes may still happen before the first beta release on March 8th. Use with caution.**

The Lean CLI is a cross-platform CLI aimed at making it easier to develop with the LEAN engine locally and in the cloud.

Visit the [documentation website](https://www.quantconnect.com/docs/v2/lean-cli/getting-started/lean-cli) for comprehensive and up-to-date documentation.

## Installation

The CLI can be installed and updated by running `pip install --upgrade lean`.

Note that many commands in the CLI require Docker to run. See [Get Docker](https://docs.docker.com/get-docker/) for instructions on how to install Docker for your operating system.

After installing the CLI, simply `cd` into an empty directory and run `lean init` to set up a Lean CLI directory. This will scaffold a standard directory structure for you to hit the ground running.

## Usage

The Lean CLI supports multiple workflows. The examples below serve as a starting point, you're free to mix local and cloud features in any way you'd like.

A cloud-focused workflow (local development, cloud execution) with the CLI may look like this:
1. Open a terminal in the Lean CLI directory.
2. Run `lean cloud pull` to pull remotely changed files.
3. Start programming locally and run backtests in the cloud with `lean cloud backtest "Project Name" --open --push` whenever there is something to backtest. The `--open` flag means that the backtest results will be opened in the browser when done, while the `--push` flag means that local changes are pushed to the cloud before running the backtest.
4. Whenever you want to create a new project, run `lean create-project "Project Name"` and `lean cloud push --project "Project Name"` to create a new project containing some basic code and to push it to the cloud.
5. When you're finished for the moment, run `lean cloud push` to push all locally changed files to the cloud.

A locally-focused workflow (local development, local execution) with the CLI may look like this:
1. Open a terminal in the Lean CLI directory.
2. Run `lean create-project "Project Name"` to create a new project with some basic code to get you started.
3. Work on your strategy in `./Project Name`.
4. Run `lean research "Project Name"` to start a Jupyter Lab session to perform research in.
5. Run `lean backtest "Project Name"` to run a backtest whenever there's something to test. This runs your strategy in a Docker container containing the same packages as the ones used on QuantConnect.com, but with your own data.

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
- [x] Local data downloading
- [x] Local optimization
- [ ] Local backtest report creation
- [ ] Local backtest visualization
- [ ] Local live trading
- [ ] Cloud optimization
- [ ] Cloud live trading
- [ ] Local library support

## Commands

*Note: the readme only contains the `--help` text of all commands. Visit the [documentation website](https://www.quantconnect.com/docs/v2/lean-cli/getting-started/lean-cli) for more comprehensive documentation.*

<!-- commands start -->
- [`lean backtest`](#lean-backtest)
- [`lean cloud backtest`](#lean-cloud-backtest)
- [`lean cloud pull`](#lean-cloud-pull)
- [`lean cloud push`](#lean-cloud-push)
- [`lean config get`](#lean-config-get)
- [`lean config list`](#lean-config-list)
- [`lean config set`](#lean-config-set)
- [`lean create-project`](#lean-create-project)
- [`lean data download cfd`](#lean-data-download-cfd)
- [`lean data download forex`](#lean-data-download-forex)
- [`lean data generate`](#lean-data-generate)
- [`lean init`](#lean-init)
- [`lean login`](#lean-login)
- [`lean logout`](#lean-logout)
- [`lean optimize`](#lean-optimize)
- [`lean research`](#lean-research)

### `lean backtest`

Backtest a project locally using Docker.

```
Usage: lean backtest [OPTIONS] PROJECT

  Backtest a project locally using Docker.

  If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
  If PROJECT is a file, the algorithm in the specified file will be executed.

  Go to the following url to learn how to debug backtests locally using the Lean CLI:
  https://www.quantconnect.com/docs/v2/lean-cli/tutorials/backtesting#03-Debugging-local-backtestshtml

Options:
  --output DIRECTORY            Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP)
  --debug [pycharm|ptvsd|mono]  Enable a certain debugging method (see --help for more information)
  --update                      Pull the selected LEAN engine version before running the backtest
  --version TEXT                The LEAN engine version to run (defaults to the latest installed version)
  --lean-config FILE            The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                     Enable debug logging
  --help                        Show this message and exit.
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
  --open       Automatically open the results in the browser when the backtest is finished
  --verbose    Enable debug logging
  --help       Show this message and exit.
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
  --verbose        Enable debug logging
  --help           Show this message and exit.
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
  --verbose            Enable debug logging
  --help               Show this message and exit.
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
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/config/get.py](lean/commands/config/get.py)_

### `lean config list`

List the configurable options and their current values.

```
Usage: lean config list [OPTIONS]

  List the configurable options and their current values.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/config/list.py](lean/commands/config/list.py)_

### `lean config set`

Set a configurable option.

```
Usage: lean config set [OPTIONS] KEY VALUE

  Set a configurable option.

  Run `lean config list` to show all available options.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
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
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/create_project.py](lean/commands/create_project.py)_

### `lean data download cfd`

Download free CFD data from QuantConnect's Data Library.

```
Usage: lean data download cfd [OPTIONS]

  Download free CFD data from QuantConnect's Data Library.

  This command can only download data that you have previously added to your QuantConnect account.
  See the following url for instructions on how to do so:
  https://www.quantconnect.com/docs/v2/lean-cli/tutorials/local-data#02-QuantConnect-Data-Libraryhtml

  See the following url for the data that can be downloaded with this command:
  https://www.quantconnect.com/data/tree/cfd/oanda

  Example of downloading https://www.quantconnect.com/data/file/cfd/oanda/daily/au200aud.zip/au200aud.csv:
  $ lean download cfd --ticker au200aud --resolution daily

Options:
  --ticker TEXT                   The ticker of the data  [required]
  --resolution [tick|second|minute|hour|daily]
                                  The resolution of the data  [required]
  --start [yyyyMMdd]              The inclusive start date of the data (ignored for daily and hourly data)
  --end [yyyyMMdd]                The inclusive end date of the data (ignored for daily and hourly data)
  --overwrite                     Overwrite existing local data
  --lean-config FILE              The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/data/download/cfd.py](lean/commands/data/download/cfd.py)_

### `lean data download forex`

Download free Forex data from QuantConnect's Data Library.

```
Usage: lean data download forex [OPTIONS]

  Download free Forex data from QuantConnect's Data Library.

  This command can only download data that you have previously added to your QuantConnect account.
  See the following url for instructions on how to do so:
  https://www.quantconnect.com/docs/v2/lean-cli/tutorials/local-data#02-QuantConnect-Data-Libraryhtml

  See the following url for the data that can be downloaded with this command:
  https://www.quantconnect.com/data/tree/forex

  Example of downloading 2019 data of https://www.quantconnect.com/data/tree/forex/fxcm/minute/eurusd:
  $ lean download forex --ticker eurusd --market fxcm --resolution minute --start 20190101 --end 20191231

Options:
  --ticker TEXT                   The ticker of the data  [required]
  --market [fxcm|oanda]           The market of the data  [required]
  --resolution [tick|second|minute|hour|daily]
                                  The resolution of the data  [required]
  --start [yyyyMMdd]              The inclusive start date of the data (ignored for daily and hourly data)
  --end [yyyyMMdd]                The inclusive end date of the data (ignored for daily and hourly data)
  --overwrite                     Overwrite existing local data
  --lean-config FILE              The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/data/download/forex.py](lean/commands/data/download/forex.py)_

### `lean data generate`

Generate random market data.

```
Usage: lean data generate [OPTIONS]

  Generate random market data.

  This uses the random data generator in LEAN to generate realistic market data using a Brownian motion model.
  This generator supports the following security types, tick types and resolutions:
  | Security type | Generated tick types | Supported resolutions                |
  | ------------- | -------------------- | ------------------------------------ |
  | Equity        | Trade                | Tick, Second, Minute, Hour and Daily |
  | Forex         | Quote                | Tick, Second, Minute, Hour and Daily |
  | CFD           | Quote                | Tick, Second, Minute, Hour and Daily |
  | Future        | Trade and Quote      | Tick, Second, Minute, Hour and Daily |
  | Crypto        | Trade and Quote      | Tick, Second, Minute, Hour and Daily |
  | Option        | Trade and Quote      | Minute                               |

  The following data densities are available:
  - Dense: at least one data point per resolution step.
  - Sparse: at least one data point per 5 resolution steps.
  - VerySparse: at least one data point per 50 resolution steps.

  Example which generates minute data for 100 equity symbols since 2015-01-01:
  $ lean generate --start=20150101 --symbol-count=100

  Example which generates daily data for 100 crypto symbols since 2015-01-01:
  $ lean generate --start=20150101 --symbol-count=100 --security-type=Crypto --resolution=Daily

Options:
  --start [yyyyMMdd]              Start date for the data to generate in yyyyMMdd format  [required]
  --end [yyyyMMdd]                End date for the data to generate in yyyyMMdd format (defaults to today)
  --symbol-count INTEGER RANGE    The amount of symbols to generate data for  [required]
  --security-type [Equity|Forex|Cfd|Future|Crypto|Option]
                                  The security type to generate data for (defaults to Equity)
  --resolution [Tick|Second|Minute|Hour|Daily]
                                  The resolution of the generated data (defaults to Minute)
  --data-density [Dense|Sparse|VerySparse]
                                  The density of the generated data (defaults to Dense)
  --include-coarse BOOLEAN        Whether coarse universe data should be generated for Equity data (defaults to True)
  --update                        Pull the selected LEAN engine version before running the generator
  --version TEXT                  The LEAN engine version to use (defaults to the latest installed version)
  --lean-config FILE              The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/data/generate.py](lean/commands/data/generate.py)_

### `lean init`

Scaffold a Lean CLI directory.

```
Usage: lean init [OPTIONS]

  Scaffold a Lean CLI directory.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
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
  -u, --user-id TEXT    QuantConnect user id
  -t, --api-token TEXT  QuantConnect API token
  --verbose             Enable debug logging
  --help                Show this message and exit.
```

_See code: [lean/commands/login.py](lean/commands/login.py)_

### `lean logout`

Log out and remove stored credentials.

```
Usage: lean logout [OPTIONS]

  Log out and remove stored credentials.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/logout.py](lean/commands/logout.py)_

### `lean optimize`

Optimize a project's parameters locally using Docker.

```
Usage: lean optimize [OPTIONS] PROJECT

  Optimize a project's parameters locally using Docker.

  If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
  If PROJECT is a file, the algorithm in the specified file will be executed.

  The --optimizer-config option can be used to specify the configuration to run the optimizer with.
  When using the option it should point to a file like this (the algorithm-* properties should be omitted):
  https://github.com/QuantConnect/Lean/blob/master/Optimizer.Launcher/config.json

  When --optimizer-config is not set, an interactive prompt will be shown to configure the optimizer.

Options:
  --output DIRECTORY       Directory to store results in (defaults to PROJECT/optimizations/TIMESTAMP)
  --optimizer-config FILE  The optimizer configuration file that should be used
  --update                 Pull the selected LEAN engine version before running the optimizer
  --version TEXT           The LEAN engine version to run (defaults to the latest installed version)
  --lean-config FILE       The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                Enable debug logging
  --help                   Show this message and exit.
```

_See code: [lean/commands/optimize.py](lean/commands/optimize.py)_

### `lean research`

Run a Jupyter Lab environment locally using Docker.

```
Usage: lean research [OPTIONS] PROJECT

  Run a Jupyter Lab environment locally using Docker.

Options:
  --port INTEGER      The port to run Jupyter Lab on (defaults to 8888)
  --update            Pull the selected research environment version before starting it
  --version TEXT      The version of the research environment version to run (defaults to the latest installed version)
  --lean-config FILE  The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose           Enable debug logging
  --help              Show this message and exit.
```

_See code: [lean/commands/research.py](lean/commands/research.py)_
<!-- commands end -->

## Development

To work on the Lean CLI, clone the repository, enter an environment containing Python 3.6+ and run `pip install -r requirements.txt`. This command will install the required dependencies and installs the CLI in editable mode. This means you'll be able to edit the code and immediately see the results the next time you run `lean`.

If you need to add dependencies, first update `setup.py` (if it is a production dependency) or `requirements.txt` (if it is a development dependency) and then re-run `pip install -r requirements.txt`.

The automated tests can be ran by running `pytest`. The filesystem and HTTP requests are mocked when running tests to make sure they run in an isolated environment.

To update the commands reference part of the readme run `python scripts/readme.py` from the root of the project.

Maintainers can publish new releases by pushing a Git tag containing the new version to GitHub. This will trigger a GitHub Actions workflow which releases the current `main` branch to PyPI with the value of the tag as version. Make sure the version is not prefixed with "v".
