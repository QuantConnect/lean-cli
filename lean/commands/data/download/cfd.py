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

import click

from lean.click import DateParameter, LeanCommand
from lean.container import container
from lean.models.api import QCResolution, QCSecurityType
from lean.models.errors import MoreInfoError


@click.command(cls=LeanCommand, requires_lean_config=True)
@click.option("--ticker", type=str, required=True, help="The ticker of the data")
@click.option("--resolution",
              type=click.Choice(["tick", "second", "minute", "hour", "daily"], case_sensitive=False),
              required=True,
              help="The resolution of the data")
@click.option("--start",
              type=DateParameter(),
              help="The inclusive start date of the data (ignored for daily and hourly data)")
@click.option("--end",
              type=DateParameter(),
              help="The inclusive end date of the data (ignored for daily and hourly data)")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing local data")
def cfd(ticker: str, resolution: str, start: Optional[datetime], end: Optional[datetime], overwrite: bool) -> None:
    """Download free CFD data from QuantConnect's Data Library.

    \b
    This command can only download data that you have previously added to your QuantConnect account.
    See the following url for instructions on how to do so:
    https://www.quantconnect.com/docs/v2/lean-cli/tutorials/local-data/downloading-from-quantconnect#02-QuantConnect-Data-Library

    \b
    See the following url for the data that can be downloaded with this command:
    https://www.quantconnect.com/data/tree/cfd/oanda

    \b
    Example of downloading https://www.quantconnect.com/data/file/cfd/oanda/daily/au200aud.zip/au200aud.csv:
    $ lean download cfd --ticker au200aud --resolution daily
    """
    ticker = ticker.lower()

    if resolution == "hour" or resolution == "daily":
        start = None
        end = None
        path_template = f"cfd/oanda/{resolution}/{ticker}.zip"
    else:
        if start is None or end is None:
            raise MoreInfoError(f"Both --start and --end must be given for {resolution} resolution",
                                "https://www.quantconnect.com/docs/v2/lean-cli/tutorials/local-data/downloading-from-quantconnect#03-Downloading-data-from-Data-Library")
        path_template = f"cfd/oanda/{resolution}/{ticker}/$DAY$_quote.zip"

    data_downloader = container.data_downloader()
    data_downloader.download_data(security_type=QCSecurityType.CFD,
                                  ticker=ticker,
                                  market="oanda",
                                  resolution=QCResolution.by_name(resolution),
                                  start=start,
                                  end=end,
                                  path_template=path_template,
                                  overwrite=overwrite)
