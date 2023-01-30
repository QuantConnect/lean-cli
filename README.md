![Lean CLI](http://cdn.quantconnect.com.s3.us-east-1.amazonaws.com/i/github/lean-cli-splash.png)

# QuantConnect Lean CLI

[![Build Status](https://github.com/QuantConnect/lean-cli/workflows/Build/badge.svg)](https://github.com/QuantConnect/lean-cli/actions?query=workflow%3ABuild)
[![PyPI Version](https://img.shields.io/pypi/v/lean)](https://pypi.org/project/lean/)
[![Project Status](https://img.shields.io/pypi/status/lean)](https://pypi.org/project/lean/)

The Lean CLI is a cross-platform CLI aimed at making it easier to develop with the LEAN engine locally and in the cloud.

Visit the [documentation website](https://www.lean.io/docs/v2/lean-cli/key-concepts/getting-started) for comprehensive and up-to-date documentation.

## Highlights

- [Project scaffolding](https://www.lean.io/docs/v2/lean-cli/projects/project-management)
- [Local autocomplete](https://www.lean.io/docs/v2/lean-cli/projects/autocomplete)
- [Local data downloading](https://www.lean.io/docs/v2/lean-cli/datasets/downloading-quantconnect-data)
- [Local backtesting](https://www.lean.io/docs/v2/lean-cli/backtesting/deployment#02-Run-Local-Backtests)
- [Local debugging](https://www.lean.io/docs/v2/lean-cli/backtesting/debugging)
- [Local research environment](https://www.lean.io/docs/v2/lean-cli/research)
- [Local optimization](https://www.lean.io/docs/v2/lean-cli/optimization/deployment#02-Run-Local-Optimizations)
- [Local live trading](https://www.lean.io/docs/v2/lean-cli/live-trading/quantconnect-paper-trading#02-Deploy-Local-Algorithms)
- [Local backtest report creation](https://www.lean.io/docs/v2/lean-cli/backtesting/report#02-Generate-a-Report)
- [Cloud synchronization](https://www.lean.io/docs/v2/lean-cli/projects/cloud-synchronization)
- [Cloud backtesting](https://www.lean.io/docs/v2/lean-cli/backtesting/deployment#03-Run-Cloud-Backtests)
- [Cloud optimization](https://www.lean.io/docs/v2/lean-cli/optimization/deployment#03-Run-Cloud-Optimizations)
- [Cloud live trading](https://www.lean.io/docs/v2/lean-cli/live-trading/quantconnect-paper-trading#03-Deploy-Cloud-Algorithms)

## Installation

The CLI can be installed and updated by running `pip install --upgrade lean`.

Note that many commands in the CLI require Docker to run. See [Get Docker](https://docs.docker.com/get-docker/) for instructions on how to install Docker for your operating system.

**Note:** Some Linux users may need to install `tkinter` using the following commands:

``` 
For Python 3

sudo apt-get install python3-tk

For Python 2.7

sudo apt-get install python-tk
```
After installing the CLI, open a terminal in an empty directory and run `lean init`. This command downloads the latest configuration file and sample data from the [QuantConnect/Lean](https://github.com/QuantConnect/Lean) repository. We recommend running all Lean CLI commands in the same directory `lean init` was ran in.

## Usage

The Lean CLI supports multiple workflows. The examples below serve as a starting point, you're free to mix local and cloud features in any way you'd like.

A cloud-focused workflow (local development, cloud execution) with the CLI may look like this:
1. Open a terminal in the directory you ran `lean init` in.
2. Run `lean cloud pull` to pull remotely changed files.
3. Start programming locally and run backtests in the cloud with `lean cloud backtest "Project Name" --open --push` whenever there is something to backtest. The `--open` flag means that the backtest results will be opened in the browser when done, while the `--push` flag means that local changes are pushed to the cloud before running the backtest.
4. Whenever you want to create a new project, run `lean create-project "Project Name"` and `lean cloud push --project "Project Name"` to create a new project containing some basic code and to push it to the cloud.
5. When you're finished for the moment, run `lean cloud push` to push all locally changed files to the cloud.

A locally-focused workflow (local development, local execution) with the CLI may look like this:
1. Open a terminal in the directory you ran `lean init` in.
2. Run `lean create-project "Project Name"` to create a new project with some basic code to get you started.
3. Work on your strategy in `./Project Name`.
4. Run `lean research "Project Name"` to start a Jupyter Lab session to perform research in.
5. Run `lean backtest "Project Name"` to run a backtest whenever there's something to test. This runs your strategy in a Docker container containing the same packages as the ones used on QuantConnect.com, but with your own data.

## Commands

*Note: the readme only contains the `--help` text of all commands. Visit the [documentation website](https://www.lean.io/docs/v2/lean-cli/key-concepts/getting-started) for more comprehensive documentation.*

<!-- commands start -->
- [`lean backtest`](#lean-backtest)
- [`lean build`](#lean-build)
- [`lean cloud backtest`](#lean-cloud-backtest)
- [`lean cloud live`](#lean-cloud-live)
- [`lean cloud live deploy`](#lean-cloud-live-deploy)
- [`lean cloud live liquidate`](#lean-cloud-live-liquidate)
- [`lean cloud live stop`](#lean-cloud-live-stop)
- [`lean cloud optimize`](#lean-cloud-optimize)
- [`lean cloud pull`](#lean-cloud-pull)
- [`lean cloud push`](#lean-cloud-push)
- [`lean cloud status`](#lean-cloud-status)
- [`lean config get`](#lean-config-get)
- [`lean config list`](#lean-config-list)
- [`lean config set`](#lean-config-set)
- [`lean config unset`](#lean-config-unset)
- [`lean create-project`](#lean-create-project)
- [`lean data download`](#lean-data-download)
- [`lean data generate`](#lean-data-generate)
- [`lean delete-project`](#lean-delete-project)
- [`lean init`](#lean-init)
- [`lean library add`](#lean-library-add)
- [`lean library remove`](#lean-library-remove)
- [`lean live`](#lean-live)
- [`lean live add-security`](#lean-live-add-security)
- [`lean live cancel-order`](#lean-live-cancel-order)
- [`lean live deploy`](#lean-live-deploy)
- [`lean live liquidate`](#lean-live-liquidate)
- [`lean live stop`](#lean-live-stop)
- [`lean live submit-order`](#lean-live-submit-order)
- [`lean live update-order`](#lean-live-update-order)
- [`lean login`](#lean-login)
- [`lean logout`](#lean-logout)
- [`lean logs`](#lean-logs)
- [`lean optimize`](#lean-optimize)
- [`lean project-create`](#lean-project-create)
- [`lean project-delete`](#lean-project-delete)
- [`lean report`](#lean-report)
- [`lean research`](#lean-research)
- [`lean whoami`](#lean-whoami)

### `lean backtest`

Backtest a project locally using Docker.

```
Usage: lean backtest [OPTIONS] PROJECT

  Backtest a project locally using Docker.

  If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
  If PROJECT is a file, the algorithm in the specified file will be executed.

  Go to the following url to learn how to debug backtests locally using the Lean CLI:
  https://www.lean.io/docs/v2/lean-cli/backtesting/debugging

  By default the official LEAN engine image is used. You can override this using the --image option. Alternatively you
  can set the default engine image for all commands using `lean config set engine-image <image>`.

Options:
  --output DIRECTORY              Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP)
  -d, --detach                    Run the backtest in a detached Docker container and return immediately
  --debug [pycharm|ptvsd|vsdbg|rider]
                                  Enable a certain debugging method (see --help for more information)
  --data-provider [Terminal Link|QuantConnect|Local]
                                  Update the Lean configuration file to retrieve data from the given provider
  --download-data                 Update the Lean configuration file to download data from the QuantConnect API, alias
                                  for --data-provider QuantConnect
  --data-purchase-limit INTEGER   The maximum amount of QCC to spend on downloading data during the backtest when using
                                  QuantConnect as data provider
  --release                       Compile C# projects in release configuration instead of debug
  --image TEXT                    The LEAN engine image to use (defaults to quantconnect/lean:latest)
  --python-venv TEXT              The path of the python virtual environment to be used
  --update                        Pull the LEAN engine image before running the backtest
  --backtest-name TEXT            Backtest name
  --lean-config FILE              The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/backtest.py](lean/commands/backtest.py)_

### `lean build`

Build Docker images of your own version of LEAN.

```
Usage: lean build [OPTIONS] [ROOT]

  Build Docker images of your own version of LEAN.

  ROOT must point to a directory containing the LEAN repository:
  https://github.com/QuantConnect/Lean

  When ROOT is not given, the current directory is used as root directory.

  This command performs the following actions:
  1. The lean-cli/foundation:latest image is built from Lean/DockerfileLeanFoundation(ARM).
  2. LEAN is compiled in a Docker container using the lean-cli/foundation:latest image.
  3. The lean-cli/engine:latest image is built from Lean/Dockerfile using lean-cli/foundation:latest as base image.
  4. The lean-cli/research:latest image is built from Lean/DockerfileJupyter using lean-cli/engine:latest as base image.
  5. The default engine image is set to lean-cli/engine:latest.
  6. The default research image is set to lean-cli/research:latest.

  When the foundation Dockerfile is the same as the official foundation Dockerfile, quantconnect/lean:foundation is used
  instead of building a custom foundation image.

Options:
  --tag TEXT  The tag to apply to custom images (defaults to latest)
  --verbose   Enable debug logging
  --help      Show this message and exit.
```

_See code: [lean/commands/build.py](lean/commands/build.py)_

### `lean cloud backtest`

Backtest a project in the cloud.

```
Usage: lean cloud backtest [OPTIONS] PROJECT

  Backtest a project in the cloud.

  PROJECT must be the name or id of the project to run a backtest for.

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

### `lean cloud live`

Interact with the QuantConnect cloud live deployments.

```
Usage: lean cloud live [OPTIONS] COMMAND [ARGS]...

  Interact with the QuantConnect cloud live deployments.

Options:
  --help  Show this message and exit.

Commands:
  deploy     Start live trading for a project in the cloud.
  liquidate  Stops live trading and liquidates existing positions for a certain project.
  stop       Stops live trading for a certain project without liquidating existing positions.
```

### `lean cloud live deploy`

Start live trading for a project in the cloud.

```
Usage: lean cloud live deploy [OPTIONS] PROJECT

  Start live trading for a project in the cloud.

  PROJECT must be the name or the id of the project to start live trading for.

  By default an interactive wizard is shown letting you configure the deployment. If --brokerage is given the command
  runs in non-interactive mode. In this mode the CLI does not prompt for input or confirmation. In non-interactive mode
  the options specific to the given brokerage are required, as well as --node, --auto-restart, --notify-order-events and
  --notify-insights.

Options:
  --brokerage [Paper Trading|Interactive Brokers|Tradier|Oanda|Bitfinex|Coinbase Pro|Binance|Zerodha|Samco|Trading Technologies|Kraken|TDAmeritrade]
                                  The brokerage to use
  --ib-user-name TEXT             Your Interactive Brokers username
  --ib-account TEXT               Your Interactive Brokers account id
  --ib-password TEXT              Your Interactive Brokers password
  --ib-weekly-restart-utc-time TEXT
                                  Weekly restart UTC time (hh:mm:ss). Each week on Sunday your algorithm is restarted at
                                  this time, and will require 2FA verification. This is required by Interactive Brokers.
                                  Use this option explicitly to override the default value.
  --ib-data-feed BOOLEAN          Whether the Interactive Brokers price data feed must be used instead of the
                                  QuantConnect price data feed
  --tradier-account-id TEXT       Your Tradier account id
  --tradier-access-token TEXT     Your Tradier access token
  --tradier-environment [live|paper]
                                  Whether the developer sandbox should be used
  --oanda-account-id TEXT         Your OANDA account id
  --oanda-access-token TEXT       Your OANDA API token
  --oanda-environment [Practice|Trade]
                                  The environment to run in, Practice for fxTrade Practice, Trade for fxTrade
  --bitfinex-api-key TEXT         Your Bitfinex API key
  --bitfinex-api-secret TEXT      Your Bitfinex API secret
  --gdax-api-key TEXT             Your Coinbase Pro API key
  --gdax-api-secret TEXT          Your Coinbase Pro API secret
  --gdax-passphrase TEXT          Your Coinbase Pro API passphrase
  --gdax-use-sandbox [live|paper]
                                  Whether the sandbox should be used
  --binance-exchange-name [Binance|BinanceUS]
                                  Binance exchange name [Binance, BinanceUS]
  --binance-api-key TEXT          Your Binance API key
  --binanceus-api-key TEXT        Your Binance API key
  --binance-api-secret TEXT       Your Binance API secret
  --binanceus-api-secret TEXT     Your Binance API secret
  --binance-use-testnet [live|paper]
                                  Whether the testnet should be used
  --zerodha-api-key TEXT          Your Kite Connect API key
  --zerodha-access-token TEXT     Your Kite Connect access token
  --zerodha-product-type [mis|cnc|nrml]
                                  MIS if you are targeting intraday products, CNC if you are targeting delivery
                                  products, NRML if you are targeting carry forward products
  --zerodha-trading-segment [equity|commodity]
                                  EQUITY if you are trading equities on NSE or BSE, COMMODITY if you are trading
                                  commodities on MCX
  --zerodha-history-subscription [true|false]
                                  Whether you have a history API subscription for Zerodha
  --samco-client-id TEXT          Your Samco account Client ID
  --samco-client-password TEXT    Your Samco account password
  --samco-year-of-birth TEXT      Your year of birth (YYYY) registered with Samco
  --samco-product-type [mis|cnc|nrml]
                                  MIS if you are targeting intraday products, CNC if you are targeting delivery
                                  products, NRML if you are targeting carry forward products
  --samco-trading-segment [equity|commodity]
                                  EQUITY if you are trading equities on NSE or BSE, COMMODITY if you are trading
                                  commodities on MCX
  --tt-user-name TEXT             Your Trading Technologies username
  --tt-session-password TEXT      Your Trading Technologies session password
  --tt-account-name TEXT          Your Trading Technologies account name
  --tt-rest-app-key TEXT          Your Trading Technologies REST app key
  --tt-rest-app-secret TEXT       Your Trading Technologies REST app secret
  --tt-rest-environment TEXT      The REST environment to run in
  --tt-order-routing-sender-comp-id TEXT
                                  The order routing sender comp id to use
  --kraken-api-key TEXT           Your Kraken API key
  --kraken-api-secret TEXT        Your Kraken API secret
  --kraken-verification-tier [Starter|Intermediate|Pro]
                                  Your Kraken Verification Tier
  --tdameritrade-api-key TEXT     Your TDAmeritrade API key
  --tdameritrade-access-token TEXT
                                  Your TDAmeritrade OAuth Access Token
  --tdameritrade-account-number TEXT
                                  Your TDAmeritrade account number
  --node TEXT                     The name or id of the live node to run on
  --auto-restart BOOLEAN          Whether automatic algorithm restarting must be enabled
  --notify-order-events BOOLEAN   Whether notifications must be sent for order events
  --notify-insights BOOLEAN       Whether notifications must be sent for emitted insights
  --notify-emails TEXT            A comma-separated list of 'email:subject' pairs configuring email-notifications
  --notify-webhooks TEXT          A comma-separated list of 'url:HEADER_1=VALUE_1:HEADER_2=VALUE_2:etc' pairs
                                  configuring webhook-notifications
  --notify-sms TEXT               A comma-separated list of phone numbers configuring SMS-notifications
  --notify-telegram TEXT          A comma-separated list of 'user/group Id:token(optional)' pairs configuring telegram-
                                  notifications
  --live-cash-balance TEXT        A comma-separated list of currency:amount pairs of initial cash balance
  --live-holdings TEXT            A comma-separated list of symbol:symbolId:quantity:averagePrice of initial portfolio
                                  holdings
  --push                          Push local modifications to the cloud before starting live trading
  --open                          Automatically open the live results in the browser once the deployment starts
  --show-secrets                  Show secrets as they are input
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/cloud/live/deploy.py](lean/commands/cloud/live/deploy.py)_

### `lean cloud live liquidate`

Stops live trading and liquidates existing positions for a certain project.

```
Usage: lean cloud live liquidate [OPTIONS] PROJECT

  Stops live trading and liquidates existing positions for a certain project.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/cloud/live/liquidate.py](lean/commands/cloud/live/liquidate.py)_

### `lean cloud live stop`

Stops live trading for a certain project without liquidating existing positions.

```
Usage: lean cloud live stop [OPTIONS] PROJECT

  Stops live trading for a certain project without liquidating existing positions.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/cloud/live/stop.py](lean/commands/cloud/live/stop.py)_

### `lean cloud optimize`

Optimize a project in the cloud.

```
Usage: lean cloud optimize [OPTIONS] PROJECT

  Optimize a project in the cloud.

  PROJECT must be the name or id of the project to optimize.

  An interactive prompt will be shown to configure the optimizer. If --target is given the command runs in non-
  interactive mode. In this mode the CLI does not prompt for input and the following options become required: --target,
  --target-direction, --parameter, --node and --parallel-nodes.

  In non-interactive mode the --parameter option can be provided multiple times to configure multiple parameters:
  - --parameter <name> <min value> <max value> <step size>
  - --parameter my-first-parameter 1 10 0.5 --parameter my-second-parameter 20 30 5

  In non-interactive mode the --constraint option can be provided multiple times to configure multiple constraints:
  - --constraint "<statistic> <operator> <value>"
  - --constraint "Sharpe Ratio >= 0.5" --constraint "Drawdown < 0.25"

  If the project that has to be optimized has been pulled to the local drive with `lean cloud pull` it is possible to
  use the --push option to push local modifications to the cloud before running the optimization.

Options:
  --target TEXT                   The target statistic of the optimization
  --target-direction [min|max]    Whether the target must be minimized or maximized
  --parameter <TEXT FLOAT FLOAT FLOAT>...
                                  The 'parameter min max step' pairs configuring the parameters to optimize
  --constraint TEXT               The 'statistic operator value' pairs configuring the constraints of the optimization
  --node [O2-8|O4-12|O8-16]       The node type to run the optimization on
  --parallel-nodes INTEGER        The number of nodes that may be run in parallel
  --name TEXT                     The name of the optimization (a random one is generated if not specified)
  --push                          Push local modifications to the cloud before starting the optimization
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/cloud/optimize.py](lean/commands/cloud/optimize.py)_

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

  This command will delete cloud files which don't have a local counterpart.

Options:
  --project DIRECTORY  Path to the local project to push (all local projects if not specified)
  --verbose            Enable debug logging
  --help               Show this message and exit.
```

_See code: [lean/commands/cloud/push.py](lean/commands/cloud/push.py)_

### `lean cloud status`

Show the live trading status of a project in the cloud.

```
Usage: lean cloud status [OPTIONS] PROJECT

  Show the live trading status of a project in the cloud.

  PROJECT must be the name or the id of the project to show the status for.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/cloud/status.py](lean/commands/cloud/status.py)_

### `lean config get`

Get the current value of a configurable option.

```
Usage: lean config get [OPTIONS] KEY

  Get the current value of a configurable option.

  Sensitive options like credentials cannot be retrieved this way for security reasons. Please open ~/.lean/credentials
  if you want to see your currently stored credentials.

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

### `lean config unset`

Unset a configurable option.

```
Usage: lean config unset [OPTIONS] KEY

  Unset a configurable option.

  Run `lean config list` to show all available options.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/config/unset.py](lean/commands/config/unset.py)_

### `lean create-project`

Alias for 'project-create'

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

### `lean data download`

Purchase and download data from QuantConnect Datasets.

```
Usage: lean data download [OPTIONS]

  Purchase and download data from QuantConnect Datasets.

  An interactive wizard will show to walk you through the process of selecting data, accepting the CLI API Access and
  Data Agreement and payment. After this wizard the selected data will be downloaded automatically.

  If --dataset is given the command runs in non-interactive mode. In this mode the CLI does not prompt for input or
  confirmation but only halts when the agreement must be accepted. In non-interactive mode all options specific to the
  selected dataset are required.

  See the following url for the data that can be purchased and downloaded with this command:
  https://www.quantconnect.com/datasets

Options:
  --dataset TEXT      The name of the dataset to download non-interactively
  --overwrite         Overwrite existing local data
  --lean-config FILE  The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose           Enable debug logging
  --help              Show this message and exit.
```

_See code: [lean/commands/data/download.py](lean/commands/data/download.py)_

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
  $ lean data generate --start=20150101 --symbol-count=100

  Example which generates daily data for 100 crypto symbols since 2015-01-01:
  $ lean data generate --start=20150101 --symbol-count=100 --security-type=Crypto --resolution=Daily

  By default the official LEAN engine image is used. You can override this using the --image option. Alternatively you
  can set the default engine image for all commands using `lean config set engine-image <image>`.

Options:
  --start [yyyyMMdd]              Start date for the data to generate in yyyyMMdd format  [required]
  --end [yyyyMMdd]                End date for the data to generate in yyyyMMdd format (defaults to today)
  --symbol-count INTEGER RANGE    The number of symbols to generate data for  [x>=0; required]
  --tickers TEXT                  Comma separated list of tickers to use for generated data
  --security-type [Equity|Forex|Cfd|Future|Crypto|Option]
                                  The security type to generate data for (defaults to Equity)
  --resolution [Tick|Second|Minute|Hour|Daily]
                                  The resolution of the generated data (defaults to Minute)
  --data-density [Dense|Sparse|VerySparse]
                                  The density of the generated data (defaults to Dense)
  --include-coarse BOOLEAN        Whether coarse universe data should be generated for Equity data (defaults to True)
  --market TEXT                   The market to generate data for (defaults to standard market for the security type)
  --image TEXT                    The LEAN engine image to use (defaults to quantconnect/lean:latest)
  --update                        Pull the LEAN engine image before running the generator
  --lean-config FILE              The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/data/generate.py](lean/commands/data/generate.py)_

### `lean delete-project`

Alias for 'project-delete'

```
Usage: lean delete-project [OPTIONS] PROJECT

  Delete a project locally and in the cloud if it exists.

  The project is selected by name or cloud id.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/delete_project.py](lean/commands/delete_project.py)_

### `lean init`

Scaffold a Lean configuration file and data directory.

```
Usage: lean init [OPTIONS]

  Scaffold a Lean configuration file and data directory.

Options:
  --organization TEXT             The name or id of the organization the Lean CLI will be scaffolded for
  -l, --language [python|csharp]  The default language to use for new projects
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/init.py](lean/commands/init.py)_

### `lean library add`

Add a custom library to a project.

```
Usage: lean library add [OPTIONS] PROJECT NAME

  Add a custom library to a project.

  PROJECT must be the path to the project.

  NAME must be either the name of a NuGet package (for C# projects), a PyPI package (for Python projects), or a path to
  a Lean CLI library.

  If --version is not given, and the library is a NuGet or PyPI package the package, it is pinned to the latest
  compatible version. For C# projects, this is the latest available version. For Python projects, this is the latest
  version compatible with Python 3.8 (which is what the Docker images use). For Lean CLI library projects, this is
  ignored.

  Custom C# libraries are added to your project's .csproj file, which is then restored if dotnet is on your PATH and the
  --no-local flag has not been given.

  Custom Python libraries are added to your project's requirements.txt file and are installed in your local Python
  environment so you get local autocomplete for the library. The last step can be skipped with the --no-local flag.

  C# example usage:
  $ lean library add "My CSharp Project" Microsoft.ML
  $ lean library add "My CSharp Project" Microsoft.ML --version 1.5.5
  $ lean library add "My CSharp Project" "Library/My CSharp Library"

  Python example usage:
  $ lean library add "My Python Project" tensorflow
  $ lean library add "My Python Project" tensorflow --version 2.5.0
  $ lean library add "My Python Project" "Library/My Python Library"

Options:
  --version TEXT  The version of the library to add (defaults to latest compatible version)
  --no-local      Skip making changes to your local environment
  --verbose       Enable debug logging
  --help          Show this message and exit.
```

_See code: [lean/commands/library/add.py](lean/commands/library/add.py)_

### `lean library remove`

Remove a custom library from a project.

```
Usage: lean library remove [OPTIONS] PROJECT NAME

  Remove a custom library from a project.

  PROJECT must be the path to the project directory.

  NAME must be either the name of the NuGet package (for C# projects), the PyPI package (for Python projects), or the
  path to the Lean CLI library to remove.

  Custom C# libraries are removed from the project's .csproj file, which is then restored if dotnet is on your PATH and
  the --no-local flag has not been given.

  Custom Python libraries are removed from the project's requirements.txt file.

  C# example usage:
  $ lean library remove "My CSharp Project" Microsoft.ML

  Python example usage:
  $ lean library remove "My Python Project" tensorflow

Options:
  --no-local  Skip making changes to your local environment
  --verbose   Enable debug logging
  --help      Show this message and exit.
```

_See code: [lean/commands/library/remove.py](lean/commands/library/remove.py)_

### `lean live`

Interact with the local machine.

```
Usage: lean live [OPTIONS] COMMAND [ARGS]...

  Interact with the local machine.

Options:
  --help  Show this message and exit.

Commands:
  add-security  Represents a command to add a security to the algorithm.
  cancel-order  Represents a command to cancel a specific order by id.
  deploy        Start live trading a project locally using Docker.
  liquidate     Liquidate the given symbol from the latest deployment of the given project.
  stop          Stop an already running local live trading project.
  submit-order  Represents a command to submit an order to the algorithm.
  update-order  Represents a command to update a specific order by id.
```

### `lean live add-security`

Represents a command to add a security to the algorithm.

```
Usage: lean live add-security [OPTIONS] PROJECT

  Represents a command to add a security to the algorithm.

Options:
  --ticker TEXT            The ticker of the symbol to add  [required]
  --market TEXT            The market of the symbol to add  [required]
  --security-type TEXT     The security type of the symbol to add  [required]
  --resolution TEXT        The resolution of the symbol to add
  --fill-data-forward      The fill forward behavior, true to fill forward, false otherwise - defaults to true
  --leverage DECIMAL       The leverage for the security, defaults to 2 for equity, 50 for forex, and 1 for everything
                           else
  --extended-market-hours  The extended market hours flag, true to allow pre/post market data, false for only in market
                           data
  --lean-config FILE       The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                Enable debug logging
  --help                   Show this message and exit.
```

_See code: [lean/commands/live/add_security.py](lean/commands/live/add_security.py)_

### `lean live cancel-order`

Represents a command to cancel a specific order by id.

```
Usage: lean live cancel-order [OPTIONS] PROJECT

  Represents a command to cancel a specific order by id.

Options:
  --order-id INTEGER  The order id to be cancelled  [required]
  --lean-config FILE  The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose           Enable debug logging
  --help              Show this message and exit.
```

_See code: [lean/commands/live/cancel_order.py](lean/commands/live/cancel_order.py)_

### `lean live deploy`

Start live trading a project locally using Docker.

```
Usage: lean live deploy [OPTIONS] PROJECT

  Start live trading a project locally using Docker.

  If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
  If PROJECT is a file, the algorithm in the specified file will be executed.

  By default an interactive wizard is shown letting you configure the brokerage and data feed to use. If --environment,
  --brokerage or --data-feed are given the command runs in non-interactive mode. In this mode the CLI does not prompt
  for input.

  If --environment is given it must be the name of a live environment in the Lean configuration.

  If --brokerage and --data-feed are given, the options specific to the given brokerage/data feed must also be given.
  The Lean config is used as fallback when a brokerage/data feed-specific option hasn't been passed in. If a required
  option is not given and cannot be found in the Lean config the command aborts.

  By default the official LEAN engine image is used. You can override this using the --image option. Alternatively you
  can set the default engine image for all commands using `lean config set engine-image <image>`.

Options:
  --environment TEXT              The environment to use
  --output DIRECTORY              Directory to store results in (defaults to PROJECT/live/TIMESTAMP)
  -d, --detach                    Run the live deployment in a detached Docker container and return immediately
  --brokerage [Paper Trading|Interactive Brokers|Tradier|Oanda|Bitfinex|Coinbase Pro|Binance|Zerodha|Samco|Terminal Link|Atreyu|Trading Technologies|Kraken|TDAmeritrade]
                                  The brokerage to use
  --data-feed [Interactive Brokers|Tradier|Oanda|Bitfinex|Coinbase Pro|Binance|Zerodha|Samco|Terminal Link|Kraken|TDAmeritrade|IQFeed|Polygon Data Feed|Custom data only]
                                  The data feed to use
  --data-provider [Terminal Link|QuantConnect|Local]
                                  Update the Lean configuration file to retrieve data from the given provider
  --ib-user-name TEXT             Your Interactive Brokers username
  --ib-account TEXT               Your Interactive Brokers account id
  --ib-password TEXT              Your Interactive Brokers password
  --ib-weekly-restart-utc-time TEXT
                                  Weekly restart UTC time (hh:mm:ss). Each week on Sunday your algorithm is restarted at
                                  this time, and will require 2FA verification. This is required by Interactive Brokers.
                                  Use this option explicitly to override the default value.
  --tradier-account-id TEXT       Your Tradier account id
  --tradier-access-token TEXT     Your Tradier access token
  --tradier-environment [live|paper]
                                  Whether the developer sandbox should be used
  --oanda-account-id TEXT         Your OANDA account id
  --oanda-access-token TEXT       Your OANDA API token
  --oanda-environment [Practice|Trade]
                                  The environment to run in, Practice for fxTrade Practice, Trade for fxTrade
  --bitfinex-api-key TEXT         Your Bitfinex API key
  --bitfinex-api-secret TEXT      Your Bitfinex API secret
  --gdax-api-key TEXT             Your Coinbase Pro API key
  --gdax-api-secret TEXT          Your Coinbase Pro API secret
  --gdax-passphrase TEXT          Your Coinbase Pro API passphrase
  --gdax-use-sandbox [live|paper]
                                  Whether the sandbox should be used
  --binance-exchange-name [Binance|BinanceUS]
                                  Binance exchange name [Binance, BinanceUS]
  --binance-api-key TEXT          Your Binance API key
  --binanceus-api-key TEXT        Your Binance API key
  --binance-api-secret TEXT       Your Binance API secret
  --binanceus-api-secret TEXT     Your Binance API secret
  --binance-use-testnet [live|paper]
                                  Whether the testnet should be used
  --zerodha-api-key TEXT          Your Kite Connect API key
  --zerodha-access-token TEXT     Your Kite Connect access token
  --zerodha-product-type [mis|cnc|nrml]
                                  MIS if you are targeting intraday products, CNC if you are targeting delivery
                                  products, NRML if you are targeting carry forward products
  --zerodha-trading-segment [equity|commodity]
                                  EQUITY if you are trading equities on NSE or BSE, COMMODITY if you are trading
                                  commodities on MCX
  --zerodha-history-subscription [true|false]
                                  Whether you have a history API subscription for Zerodha
  --samco-client-id TEXT          Your Samco account Client ID
  --samco-client-password TEXT    Your Samco account password
  --samco-year-of-birth TEXT      Your year of birth (YYYY) registered with Samco
  --samco-product-type [mis|cnc|nrml]
                                  MIS if you are targeting intraday products, CNC if you are targeting delivery
                                  products, NRML if you are targeting carry forward products
  --samco-trading-segment [equity|commodity]
                                  EQUITY if you are trading equities on NSE or BSE, COMMODITY if you are trading
                                  commodities on MCX
  --terminal-link-environment [Production|Beta]
                                  The environment to run in
  --terminal-link-server-host TEXT
                                  The host of the TerminalLink server
  --terminal-link-server-port INTEGER
                                  The port of the TerminalLink server
  --terminal-link-symbol-map-file FILE
                                  The path to the TerminalLink symbol map file
  --terminal-link-emsx-broker TEXT
                                  The EMSX broker to use
  --terminal-link-emsx-user-time-zone TEXT
                                  The EMSX user timezone to use
  --terminal-link-emsx-account TEXT
                                  The EMSX account to use
  --terminal-link-emsx-strategy TEXT
                                  The EMSX strategy to use
  --terminal-link-emsx-notes TEXT
                                  The EMSX notes to use
  --terminal-link-emsx-handling TEXT
                                  The EMSX handling to use
  --terminal-link-allow-modification BOOLEAN
                                  Whether modification is allowed
  --atreyu-host TEXT              The host of the Atreyu server
  --atreyu-req-port INTEGER       The Atreyu request port
  --atreyu-sub-port INTEGER       The Atreyu subscribe port
  --atreyu-username TEXT          Your Atreyu username
  --atreyu-password TEXT          Your Atreyu password
  --atreyu-client-id TEXT         Your Atreyu client id
  --atreyu-broker-mpid TEXT       The broker MPID to use
  --atreyu-locate-rqd TEXT        The locate rqd to use
  --tt-user-name TEXT             Your Trading Technologies username
  --tt-session-password TEXT      Your Trading Technologies session password
  --tt-account-name TEXT          Your Trading Technologies account name
  --tt-rest-app-key TEXT          Your Trading Technologies REST app key
  --tt-rest-app-secret TEXT       Your Trading Technologies REST app secret
  --tt-rest-environment TEXT      The REST environment to run in
  --tt-market-data-sender-comp-id TEXT
                                  The market data sender comp id to use
  --tt-market-data-target-comp-id TEXT
                                  The market data target comp id to use
  --tt-market-data-host TEXT      The host of the market data server
  --tt-market-data-port TEXT      The port of the market data server
  --tt-order-routing-sender-comp-id TEXT
                                  The order routing sender comp id to use
  --tt-order-routing-target-comp-id TEXT
                                  The order routing target comp id to use
  --tt-order-routing-host TEXT    The host of the order routing server
  --tt-order-routing-port TEXT    The port of the order routing server
  --tt-log-fix-messages BOOLEAN   Whether FIX messages should be logged
  --kraken-api-key TEXT           Your Kraken API key
  --kraken-api-secret TEXT        Your Kraken API secret
  --kraken-verification-tier [Starter|Intermediate|Pro]
                                  Your Kraken Verification Tier
  --tdameritrade-api-key TEXT     Your TDAmeritrade API key
  --tdameritrade-access-token TEXT
                                  Your TDAmeritrade OAuth Access Token
  --tdameritrade-account-number TEXT
                                  Your TDAmeritrade account number
  --ib-enable-delayed-streaming-data BOOLEAN
                                  Whether delayed data may be used when your algorithm subscribes to a security you
                                  don't have a market data subscription for
  --iqfeed-iqconnect TEXT         The path to the IQConnect binary
  --iqfeed-username TEXT          Your IQFeed username
  --iqfeed-password TEXT          Your IQFeed password
  --iqfeed-productName TEXT       The product name of your IQFeed developer account
  --iqfeed-version TEXT           The product version of your IQFeed developer account
  --polygon-api-key TEXT          Your Polygon data feed API Key
  --release                       Compile C# projects in release configuration instead of debug
  --image TEXT                    The LEAN engine image to use (defaults to quantconnect/lean:latest)
  --python-venv TEXT              The path of the python virtual environment to be used
  --live-cash-balance TEXT        A comma-separated list of currency:amount pairs of initial cash balance
  --live-holdings TEXT            A comma-separated list of symbol:symbolId:quantity:averagePrice of initial portfolio
                                  holdings
  --update                        Pull the LEAN engine image before starting live trading
  --show-secrets                  Show secrets as they are input
  --lean-config FILE              The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/live/deploy.py](lean/commands/live/deploy.py)_

### `lean live liquidate`

Liquidate the given symbol from the latest deployment of the given project.

```
Usage: lean live liquidate [OPTIONS] PROJECT

  Liquidate the given symbol from the latest deployment of the given project.

Options:
  --ticker TEXT         The ticker of the symbol to liquidate
  --market TEXT         The market of the symbol to liquidate
  --security-type TEXT  The security type of the symbol to liquidate
  --lean-config FILE    The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose             Enable debug logging
  --help                Show this message and exit.
```

_See code: [lean/commands/live/liquidate.py](lean/commands/live/liquidate.py)_

### `lean live stop`

Stop an already running local live trading project.

```
Usage: lean live stop [OPTIONS] PROJECT

  Stop an already running local live trading project.

Options:
  --lean-config FILE  The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose           Enable debug logging
  --help              Show this message and exit.
```

_See code: [lean/commands/live/stop.py](lean/commands/live/stop.py)_

### `lean live submit-order`

Represents a command to submit an order to the algorithm.

```
Usage: lean live submit-order [OPTIONS] PROJECT

  Represents a command to submit an order to the algorithm.

Options:
  --ticker TEXT          The ticker of the symbol to be submitted  [required]
  --market TEXT          The market of the symbol to be submitted  [required]
  --security-type TEXT   The security type of the symbol to be submitted  [required]
  --order-type TEXT      The order type to be submitted  [required]
  --quantity DECIMAL     The number of units to be ordered (directional)  [required]
  --limit-price DECIMAL  The limit price of the order be submitted
  --stop-price DECIMAL   The stop price of the order to be submitted
  --tag TEXT             The tag to be attached to the order
  --lean-config FILE     The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose              Enable debug logging
  --help                 Show this message and exit.
```

_See code: [lean/commands/live/submit_order.py](lean/commands/live/submit_order.py)_

### `lean live update-order`

Represents a command to update a specific order by id.

```
Usage: lean live update-order [OPTIONS] PROJECT

  Represents a command to update a specific order by id.

Options:
  --order-id INTEGER     The order id to be updated  [required]
  --quantity DECIMAL     The number of units to be updated (directional)
  --limit-price DECIMAL  The limit price of the order to be updated
  --stop-price DECIMAL   The stop price of the order to be updated
  --tag TEXT             The tag to be attached to the order
  --lean-config FILE     The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose              Enable debug logging
  --help                 Show this message and exit.
```

_See code: [lean/commands/live/update_order.py](lean/commands/live/update_order.py)_

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
  --show-secrets        Show secrets as they are input
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

### `lean logs`

Display the most recent backtest/live/optimization logs.

```
Usage: lean logs [OPTIONS]

  Display the most recent backtest/live/optimization logs.

Options:
  --backtest           Display the most recent backtest logs (default)
  --live               Display the most recent live logs
  --optimization       Display the most recent optimization logs
  --project DIRECTORY  The project to get the most recent logs from
  --lean-config FILE   The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose            Enable debug logging
  --help               Show this message and exit.
```

_See code: [lean/commands/logs.py](lean/commands/logs.py)_

### `lean optimize`

Optimize a project's parameters locally using Docker.

```
Usage: lean optimize [OPTIONS] PROJECT

  Optimize a project's parameters locally using Docker.

  If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
  If PROJECT is a file, the algorithm in the specified file will be executed.

  By default an interactive wizard is shown letting you configure the optimizer. If --optimizer-config or --strategy is
  given the command runs in non-interactive mode. In this mode the CLI does not prompt for input.

  The --optimizer-config option can be used to specify the configuration to run the optimizer with.
  When using the option it should point to a file like this (the algorithm-* properties should be omitted):
  https://github.com/QuantConnect/Lean/blob/master/Optimizer.Launcher/config.json

  If --strategy is given the optimizer configuration is read from the given options. In this case --strategy, --target,
  --target-direction and --parameter become required.

  In non-interactive mode the --parameter option can be provided multiple times to configure multiple parameters:
  - --parameter <name> <min value> <max value> <step size>
  - --parameter my-first-parameter 1 10 0.5 --parameter my-second-parameter 20 30 5

  In non-interactive mode the --constraint option can be provided multiple times to configure multiple constraints:
  - --constraint "<statistic> <operator> <value>"
  - --constraint "Sharpe Ratio >= 0.5" --constraint "Drawdown < 0.25"

  If --estimate is given, the optimization will not be executed.
  The runtime estimate for the optimization will be calculated and outputted.

  By default the official LEAN engine image is used. You can override this using the --image option. Alternatively you
  can set the default engine image for all commands using `lean config set engine-image <image>`.

Options:
  --output DIRECTORY              Directory to store results in (defaults to PROJECT/optimizations/TIMESTAMP)
  -d, --detach                    Run the optimization in a detached Docker container and return immediately
  --optimizer-config FILE         The optimizer configuration file that should be used
  --strategy [Grid Search|Euler Search]
                                  The optimization strategy to use
  --target TEXT                   The target statistic of the optimization
  --target-direction [min|max]    Whether the target must be minimized or maximized
  --parameter <TEXT FLOAT FLOAT FLOAT>...
                                  The 'parameter min max step' pairs configuring the parameters to optimize
  --constraint TEXT               The 'statistic operator value' pairs configuring the constraints of the optimization
  --release                       Compile C# projects in release configuration instead of debug
  --image TEXT                    The LEAN engine image to use (defaults to quantconnect/lean:latest)
  --update                        Pull the LEAN engine image before running the optimizer
  --estimate                      Estimate optimization runtime without running it
  --max-concurrent-backtests INTEGER RANGE
                                  Maximum number of concurrent backtests to run  [x>=1]
  --lean-config FILE              The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/optimize.py](lean/commands/optimize.py)_

### `lean project-create`

Create a new project containing starter code.

```
Usage: lean project-create [OPTIONS] NAME

  Create a new project containing starter code.

  If NAME is a path containing subdirectories those will be created automatically.

  The default language can be set using `lean config set default-language python/csharp`.

Options:
  -l, --language [python|csharp]  The language of the project to create
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/project_create.py](lean/commands/project_create.py)_

### `lean project-delete`

Delete a project locally and in the cloud if it exists.

```
Usage: lean project-delete [OPTIONS] PROJECT

  Delete a project locally and in the cloud if it exists.

  The project is selected by name or cloud id.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/project_delete.py](lean/commands/project_delete.py)_

### `lean report`

Generate a report of a backtest.

```
Usage: lean report [OPTIONS]

  Generate a report of a backtest.

  This runs the LEAN Report Creator in Docker to generate a polished, professional-grade report of a backtest.

  If --backtest-results is not given, a report is generated for the most recent local backtest.

  The name, description, and version are optional and will be blank if not given.

  If the given backtest data source file is stored in a project directory (or one of its subdirectories, like the
  default <project>/backtests/<timestamp>), the default name is the name of the project directory and the default
  description is the description stored in the project's config.json file.

  By default the official LEAN engine image is used. You can override this using the --image option. Alternatively you
  can set the default engine image for all commands using `lean config set engine-image <image>`.

Options:
  --backtest-results FILE      Path to the JSON file containing the backtest results
  --live-results FILE          Path to the JSON file containing the live trading results
  --report-destination FILE    Path where the generated report is stored as HTML (defaults to ./report.html)
  -d, --detach                 Run the report creator in a detached Docker container and return immediately
  --strategy-name TEXT         Name of the strategy, will appear at the top-right corner of each page
  --strategy-version TEXT      Version number of the strategy, will appear next to the project name
  --strategy-description TEXT  Description of the strategy, will appear under the 'Strategy Description' section
  --overwrite                  Overwrite --report-destination if it already contains a file
  --image TEXT                 The LEAN engine image to use (defaults to quantconnect/lean:latest)
  --update                     Pull the LEAN engine image before running the report creator
  --lean-config FILE           The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                    Enable debug logging
  --help                       Show this message and exit.
```

_See code: [lean/commands/report.py](lean/commands/report.py)_

### `lean research`

Run a Jupyter Lab environment locally using Docker.

```
Usage: lean research [OPTIONS] PROJECT

  Run a Jupyter Lab environment locally using Docker.

  By default the official LEAN research image is used. You can override this using the --image option. Alternatively you
  can set the default research image using `lean config set research-image <image>`.

Options:
  --port INTEGER                  The port to run Jupyter Lab on (defaults to 8888)
  --data-provider [Terminal Link|QuantConnect|Local]
                                  Update the Lean configuration file to retrieve data from the given provider
  --download-data                 Update the Lean configuration file to download data from the QuantConnect API, alias
                                  for --data-provider QuantConnect
  --data-purchase-limit INTEGER   The maximum amount of QCC to spend on downloading data during the research session
                                  when using QuantConnect as data provider
  -d, --detach                    Run Jupyter Lab in a detached Docker container and return immediately
  --no-open                       Don't open the Jupyter Lab environment in the browser after starting it
  --image TEXT                    The LEAN research image to use (defaults to quantconnect/research:latest)
  --update                        Pull the LEAN research image before starting the research environment
  --lean-config FILE              The Lean configuration file that should be used (defaults to the nearest lean.json)
  --verbose                       Enable debug logging
  --help                          Show this message and exit.
```

_See code: [lean/commands/research.py](lean/commands/research.py)_

### `lean whoami`

Display who is logged in.

```
Usage: lean whoami [OPTIONS]

  Display who is logged in.

Options:
  --verbose  Enable debug logging
  --help     Show this message and exit.
```

_See code: [lean/commands/whoami.py](lean/commands/whoami.py)_
<!-- commands end -->

## Development

To work on the Lean CLI, clone the repository, enter an environment containing Python 3.7+ and run `pip install -r requirements.txt`. This command will install the required dependencies and installs the CLI in editable mode. This means you'll be able to edit the code and immediately see the results the next time you run `lean`.

If you need to add dependencies, first update `setup.py` (if it is a production dependency) or `requirements.txt` (if it is a development dependency) and then re-run `pip install -r requirements.txt`.

The automated tests can be ran by running `pytest`. The filesystem and HTTP requests are mocked when running tests to make sure they run in an isolated environment.

Can build the lean CLI by running `python setup.py sdist bdist_wheel` from the root of the project and to install it `pip install --force-reinstall dist/lean-dev-py3-none-any.whl`. To update the commands reference part of the readme run `python scripts/readme.py` from the root of the project, after installing the new version.

Maintainers can publish new releases by pushing a Git tag containing the new version to GitHub. This will trigger a GitHub Actions workflow which releases the current `master` branch to PyPI with the value of the tag as version. Make sure the version is not prefixed with "v".
