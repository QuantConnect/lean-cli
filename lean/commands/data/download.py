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

import click

from lean.click import LeanCommand


@click.command(cls=LeanCommand, requires_lean_config=True)
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing local data")
def download(overwrite: bool) -> None:
    """Purchase and download data from QuantConnect's Data Library.

    An interactive wizard will show to walk you through the process of selecting data,
    agreeing to the distribution agreements and payment.
    After this wizard the selected data will be downloaded automatically.

    \b
    See the following url for the data that can be purchased and downloaded with this command:
    https://www.quantconnect.com/data/tree
    """
    # TODO: Implement
