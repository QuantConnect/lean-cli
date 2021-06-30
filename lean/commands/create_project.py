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

from lean.click import LeanCommand
from lean.container import container
from lean.models.api import QCLanguage
from lean.models.errors import MoreInfoError

DEFAULT_PYTHON_MAIN = '''
from AlgorithmImports import *


class $CLASS_NAME$(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2013, 10, 7)  # Set Start Date
        self.SetEndDate(2013, 10, 11)  # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        self.AddEquity("SPY", Resolution.Minute)

    def OnData(self, data):
        """OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            Arguments:
                data: Slice object keyed by symbol containing the stock data
        """
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)
            self.Debug("Purchased Stock")
'''.strip() + "\n"

LIBRARY_PYTHON_MAIN = '''
from AlgorithmImports import *


class $CLASS_NAME$:
    """
    To use this library place this at the top:
    from $PROJECT_NAME$.main import $CLASS_NAME$

    Then instantiate the class:
    x = $CLASS_NAME$()
    x.Add(1, 2)
    """

    def Add(self, a, b):
        return a + b

    def Subtract(self, a, b):
        return a - b
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
                "ema = qb.Indicator(ExponentialMovingAverage(10), spy.Symbol, 360, Resolution.Daily)\\n",
                "ema.plot()"
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
    public class $CLASS_NAME$ : QCAlgorithm
    {
        public override void Initialize()
        {
            SetStartDate(2013, 10, 7); // Set Start Date
            SetEndDate(2013, 10, 11); // Set Start Date
            SetCash(100000); // Set Strategy Cash
            AddEquity("SPY", Resolution.Minute);
        }

        /// OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
        /// Slice object keyed by symbol containing the stock data
        public override void OnData(Slice data)
        {
            if (!Portfolio.Invested)
            {
                SetHoldings("SPY", 1);
                Debug("Purchased Stock");
            }
        }
    }
}
""".strip() + "\n"

LIBRARY_CSHARP_MAIN = """
namespace QuantConnect
{
    public class $CLASS_NAME$
    {
        /*
         * To use this library, first add it to a solution and create a project reference in your algorithm project:
         * https://www.lean.io/docs/lean-cli/tutorials/code-sharing#02-C-code-sharing
         *
         * Then add its namespace at the top of the page:
         * using QuantConnect;
         *
         * Then instantiate the class:
         * var x = new $CLASS_NAME$();
         * x.Add(1, 2);
         */

        public int Add(int a, int b)
        {
            return a + b;
        }

        public int Subtract(int a, int b)
        {
            return a - b;
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
                "// We need to load assemblies at the start in their own cell\\n",
                "#load \\"../Initialize.csx\\""
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
                "\\n",
                "using QuantConnect;\\n",
                "using QuantConnect.Data;\\n",
                "using QuantConnect.Research;\\n",
                "using QuantConnect.Algorithm;\\n",
                "\\n",
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
            "display_name": ".NET (C#)",
            "language": "C#",
            "name": ".net-csharp"
        },
        "language_info": {
            "file_extension": ".cs",
            "mimetype": "text/x-csharp",
            "name": "C#",
            "pygments_lexer": "csharp",
            "version": "9.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}
""".strip() + "\n"


def _capitalize(word: str) -> str:
    """Capitalizes the given word.

    :param word: the word to capitalize
    :return: the word with the first letter capitalized (any other uppercase characters are preserved)
    """
    if word == "":
        return word
    return word[0].upper() + word[1:]


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
        raise MoreInfoError(
            "Please specify a language with --language or set the default language using `lean config set default-language python/csharp`",
            "https://www.lean.io/docs/lean-cli/tutorials/project-management")

    full_path = Path.cwd() / name

    if not container.path_manager().is_path_valid(full_path):
        raise MoreInfoError(f"'{name}' is not a valid path",
                            "https://www.lean.io/docs/lean-cli/user-guides/troubleshooting#02-Common-errors")

    is_library_project = False
    try:
        library_dir = container.lean_config_manager().get_cli_root_directory() / "Library"
        is_library_project = library_dir in full_path.parents
    except:
        # get_cli_root_directory() raises an error if there is no such directory
        pass

    if is_library_project and language == "python" and not full_path.name.isidentifier():
        raise RuntimeError(
            f"'{full_path.name}' is not a valid Python identifier, which is required for Python library projects to be importable")

    if full_path.exists():
        raise RuntimeError(f"A project named '{name}' already exists, please choose a different name")
    else:
        project_manager = container.project_manager()
        project_manager.create_new_project(full_path, QCLanguage.Python if language == "python" else QCLanguage.CSharp)

    # Convert the project name into a valid class name by removing all non-alphanumeric characters
    class_name = re.sub(f"[^a-zA-Z0-9]", "", "".join(map(_capitalize, full_path.name.split(" "))))

    if language == "python":
        main_name = "main.py"
        main_content = DEFAULT_PYTHON_MAIN if not is_library_project else LIBRARY_PYTHON_MAIN
    else:
        main_name = "Main.cs"
        main_content = DEFAULT_CSHARP_MAIN if not is_library_project else LIBRARY_CSHARP_MAIN

    with (full_path / main_name).open("w+", encoding="utf-8") as file:
        file.write(main_content.replace("$CLASS_NAME$", class_name).replace("$PROJECT_NAME$", full_path.name))

    with (full_path / "research.ipynb").open("w+", encoding="utf-8") as file:
        file.write(DEFAULT_PYTHON_NOTEBOOK if language == "python" else DEFAULT_CSHARP_NOTEBOOK)

    logger = container.logger()
    logger.info(f"Successfully created {'Python' if language == 'python' else 'C#'} project '{name}'")
