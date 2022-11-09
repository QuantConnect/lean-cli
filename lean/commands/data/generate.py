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

from datetime import datetime
from typing import Optional

from click import command, option, Choice, IntRange

from lean.click import DateParameter, LeanCommand
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@option("--start",
              type=DateParameter(),
              required=True,
              help="Start date for the data to generate in yyyyMMdd format")
@option("--end",
              type=DateParameter(),
              default=datetime.today().strftime("%Y%m%d"),
              help="End date for the data to generate in yyyyMMdd format (defaults to today)")
@option("--symbol-count",
              type=IntRange(min=0),
              required=True,
              help="The number of symbols to generate data for")
@option("--tickers",
              type=str,
              required=False,
              default="",
              help="Comma separated list of tickers to use for generated data")
@option("--security-type",
              type=Choice(["Equity", "Forex", "Cfd", "Future", "Crypto", "Option"], case_sensitive=False),
              default="Equity",
              help="The security type to generate data for (defaults to Equity)")
@option("--resolution",
              type=Choice(["Tick", "Second", "Minute", "Hour", "Daily"], case_sensitive=False),
              default="Minute",
              help="The resolution of the generated data (defaults to Minute)")
@option("--data-density",
              type=Choice(["Dense", "Sparse", "VerySparse"], case_sensitive=False),
              default="Dense",
              help="The density of the generated data (defaults to Dense)")
@option("--include-coarse",
              type=bool,
              default=True,
              help="Whether coarse universe data should be generated for Equity data (defaults to True)")
@option("--market",
              type=str,
              default="",
              help="The market to generate data for (defaults to standard market for the security type)")
@option("--image",
              type=str,
              help=f"The LEAN engine image to use (defaults to {DEFAULT_ENGINE_IMAGE})")
@option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN engine image before running the generator")
def generate(start: datetime,
             end: datetime,
             symbol_count: int,
             tickers: str,
             security_type: str,
             resolution: str,
             data_density: str,
             include_coarse: bool,
             market: str,
             image: Optional[str],
             update: bool) -> None:
    """Generate random market data.

    \b
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

    \b
    The following data densities are available:
    - Dense: at least one data point per resolution step.
    - Sparse: at least one data point per 5 resolution steps.
    - VerySparse: at least one data point per 50 resolution steps.

    \b
    Example which generates minute data for 100 equity symbols since 2015-01-01:
    $ lean data generate --start=20150101 --symbol-count=100

    \b
    Example which generates daily data for 100 crypto symbols since 2015-01-01:
    $ lean data generate --start=20150101 --symbol-count=100 --security-type=Crypto --resolution=Daily

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    lean_config_manager = container.lean_config_manager
    data_dir = lean_config_manager.get_data_directory()

    entrypoint = ["dotnet", "QuantConnect.ToolBox.dll",
                  "--destination-dir", "/Lean/Data",
                  "--app", "randomdatagenerator",
                  "--start", start.strftime("%Y%m%d"),
                  "--end", end.strftime("%Y%m%d"),
                  "--symbol-count", str(symbol_count),
                  "--security-type", security_type,
                  "--resolution", resolution,
                  "--data-density", data_density,
                  "--include-coarse", str(include_coarse).lower(),
                  "--market", market.lower()]

    # Toolbox uses '--opt=val' as single argument
    if tickers:
        entrypoint.append("--tickers=" + tickers)

    run_options = {
        "entrypoint": entrypoint,
        "volumes": {
            str(data_dir): {
                "bind": "/Lean/Data",
                "mode": "rw"
            }
        }
    }

    engine_image = container.cli_config_manager.get_engine_image(image)

    container.update_manager.pull_docker_image_if_necessary(engine_image, update)

    success = container.docker_manager.run_image(engine_image, **run_options)
    if not success:
        raise RuntimeError(
            "Something went wrong while running the random data generator, see the logs above for more information")
