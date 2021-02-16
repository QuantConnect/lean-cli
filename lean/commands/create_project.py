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

import re
from pathlib import Path

import click

# The default templates are coming from the "Create New Algorithm" feature in the Algorithm Lab
from lean.click import LeanCommand
from lean.container import container

DEFAULT_PYTHON_MAIN = '''
from QuantConnect import Resolution
from QuantConnect.Algorithm import QCAlgorithm


class $NAME$(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 8, 2)  # Set Start Date
        self.SetCash(100000)  # Set Strategy Cash
        # self.AddEquity("SPY", Resolution.Minute)

    def OnData(self, data):
        """OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            Arguments:
                data: Slice object keyed by symbol containing the stock data
        """
        # if not self.Portfolio.Invested:
        #     self.SetHoldings("SPY", 1)
        #     self.Debug("Purchased Stock")
'''.strip() + "\n"

DEFAULT_PYTHON_NOTEBOOK = """
{
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "![QuantConnect Logo](https://cdn.quantconnect.com/web/i/icon.png)\\n",
                "<hr>"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": null,
            "metadata": {},
            "outputs": [],
            "source": [
                "# QuantBook Analysis Tool\\n",
                "# For more information see https://www.quantconnect.com/docs/research/overview\\n",
                "qb = QuantBook()\\n",
                "spy = qb.AddEquity(\\"SPY\\")\\n",
                "history = qb.History(qb.Securities.Keys, 360, Resolution.Daily)\\n",
                "\\n",
                "# Indicator Analysis\\n",
                "bbdf = qb.Indicator(ExponentialMovingAverage(10), spy.Symbol, 360, Resolution.Daily)\\n",
                "bbdf.plot()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": null,
            "metadata": {},
            "outputs": [],
            "source": []
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.6.8"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}
""".strip() + "\n"

DEFAULT_CSHARP_MAIN = """
using QuantConnect.Data;

namespace QuantConnect.Algorithm.CSharp
{
    public class $NAME$ : QCAlgorithm
    {
        public override void Initialize()
        {
            SetStartDate(2020, 8, 2); // Set Start Date
            SetCash(100000); // Set Strategy Cash
            // AddEquity("SPY", Resolution.Minute);
        }

        /// OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
        /// Slice object keyed by symbol containing the stock data
        public override void OnData(Slice data)
        {
            // if (!Portfolio.Invested)
            // {
            //     SetHoldings("SPY", 1);
            //     Debug("Purchased Stock");
            // }
        }
    }
}
""".strip() + "\n"

DEFAULT_CSHARP_NOTEBOOK = """
{
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "![QuantConnect Logo](https://cdn.quantconnect.com/web/i/icon.png)\\n",
                "<hr>"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": null,
            "metadata": {},
            "outputs": [],
            "source": [
                "// QuantBook C# Research Environment\\n",
                "// For more information see https://www.quantconnect.com/docs/research/overview\\n",
                "#load \\"../QuantConnect.csx\\"\\n",
                "var qb = new QuantBook();\\n",
                "var spy = qb.AddEquity(\\"SPY\\");\\n",
                "var history = qb.History(qb.Securities.Keys, 360, Resolution.Daily);"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": null,
            "metadata": {},
            "outputs": [],
            "source": [
                "foreach (var slice in history.Take(5)) {\\n",
                "    Console.WriteLine(slice.Bars[spy.Symbol].ToString());\\n",
                "}"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": null,
            "metadata": {},
            "outputs": [],
            "source": []
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "C#",
            "language": "csharp",
            "name": "csharp"
        },
        "language_info": {
            "file_extension": ".cs",
            "mimetype": "text/x-csharp",
            "name": "C#",
            "pygments_lexer": "c#",
            "version": "4.0.30319"
        },
        "pycharm": {
            "stem_cell": {
                "cell_type": "raw",
                "source": [],
                "metadata": {
                    "collapsed": false
                }
            }
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}
""".strip() + "\n"


@click.command(cls=LeanCommand)
@click.argument("name", type=str)
@click.option("--language", "-l",
              type=click.Choice(container.cli_config_manager().default_language.allowed_values, case_sensitive=False),
              help="The language of the project to create")
def create_project(name: str, language: str) -> None:
    """Create a new project containing starter code.

    If NAME is a path containing subdirectories those will be created automatically.

    The default language can be set using `lean config set default-language python/csharp`.
    """
    cli_config_manager = container.cli_config_manager()

    language = language if language is not None else cli_config_manager.default_language.get_value()
    if language is None:
        raise RuntimeError(
            "Please specify a language with --language or set the default language using `lean config set default-language python/csharp`")

    full_path = Path.cwd() / name
    if full_path.exists():
        raise RuntimeError(f"A project named '{name}' already exists")
    else:
        full_path.mkdir(parents=True)

    # Convert the project name into a valid class name by removing all non-alphanumeric characters
    class_name = re.sub(f"[^a-zA-Z0-9]", "", full_path.name)

    if language == "python":
        with (full_path / "main.py").open("w+") as file:
            file.write(DEFAULT_PYTHON_MAIN.replace("$NAME$", class_name))
    else:
        with (full_path / "Main.cs").open("w+") as file:
            file.write(DEFAULT_CSHARP_MAIN.replace("$NAME$", class_name))

    with (full_path / "research.ipynb").open("w+") as file:
        file.write(DEFAULT_PYTHON_NOTEBOOK if language == "python" else DEFAULT_CSHARP_NOTEBOOK)

    project_config_manager = container.project_config_manager()
    project_config = project_config_manager.get_project_config(full_path)
    project_config.set("algorithm-language", "Python" if language == "python" else "CSharp")
    project_config.set("parameters", {})

    logger = container.logger()
    logger.info(f"Successfully created project '{name}'")
