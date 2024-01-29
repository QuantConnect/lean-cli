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

from pathlib import Path
from click import Choice, option, argument

from lean.click import LeanCommand
from lean.commands import lean
from lean.container import container
from lean.models.api import QCLanguage
from lean.models.errors import MoreInfoError
from lean.components.util.name_extraction import convert_to_class_name
from lean.components import reserved_names

DEFAULT_PYTHON_MAIN = '''
# region imports
from AlgorithmImports import *
# endregion

class $CLASS_NAME$(QCAlgorithm):

    def Initialize(self):
        # Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data
        self.SetStartDate(2013, 10, 7)  # Set Start Date
        self.SetEndDate(2013, 10, 11)  # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        self.AddEquity("SPY", Resolution.Minute)

    def OnData(self, data: Slice):
        """OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            Arguments:
                data: Slice object keyed by symbol containing the stock data
        """
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)
            self.Debug("Purchased Stock")
'''.strip() + "\n"

LIBRARY_PYTHON_MAIN = '''
#region imports
from AlgorithmImports import *
#endregion


### Library classes are snippets of code/classes you can reuse between projects. They are
### added to projects on compile.
###
### To import this class use the following import with your values subbed in for the {} sections:
### from {libraryProjectName} import Library
###
### Example using your newly imported library from 'Library.py' like so:
###
### from $PROJECT_NAME$ import Library
### x = Library.Add(1,1)
### print(x)
###

def Add(a: int, b: int):
    return a + b
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
                "# QuantBook Analysis Tool \\n",
                "# For more information see [https://www.quantconnect.com/docs/v2/our-platform/research/getting-started]\\n",
                "qb = QuantBook()\\n",
                "spy = qb.AddEquity(\\"SPY\\")\\n",
                "# Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data \\n",
                "qb.SetStartDate(2013, 10, 11)\\n",
                "history = qb.History(qb.Securities.Keys, 360, Resolution.Daily)\\n",
                "\\n",
                "# Indicator Analysis\\n",
                "bbdf = qb.Indicator(BollingerBands(30, 2), spy.Symbol, 360, Resolution.Daily)\\n",
                "bbdf.drop('standarddeviation', axis=1).plot()"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}
""".strip() + "\n"

DEFAULT_CSHARP_MAIN = """
#region imports
    using System;
    using System.Collections;
    using System.Collections.Generic;
    using System.Linq;
    using System.Globalization;
    using System.Drawing;
    using QuantConnect;
    using QuantConnect.Algorithm.Framework;
    using QuantConnect.Algorithm.Framework.Selection;
    using QuantConnect.Algorithm.Framework.Alphas;
    using QuantConnect.Algorithm.Framework.Portfolio;
    using QuantConnect.Algorithm.Framework.Portfolio.SignalExports;
    using QuantConnect.Algorithm.Framework.Execution;
    using QuantConnect.Algorithm.Framework.Risk;
    using QuantConnect.Api;
    using QuantConnect.Parameters;
    using QuantConnect.Benchmarks;
    using QuantConnect.Brokerages;
    using QuantConnect.Configuration;
    using QuantConnect.Util;
    using QuantConnect.Interfaces;
    using QuantConnect.Algorithm;
    using QuantConnect.Indicators;
    using QuantConnect.Data;
    using QuantConnect.Data.Auxiliary;
    using QuantConnect.Data.Consolidators;
    using QuantConnect.Data.Custom;
    using QuantConnect.Data.Custom.IconicTypes;
    using QuantConnect.DataSource;
    using QuantConnect.Data.Fundamental;
    using QuantConnect.Data.Market;
    using QuantConnect.Data.Shortable;
    using QuantConnect.Data.UniverseSelection;
    using QuantConnect.Notifications;
    using QuantConnect.Orders;
    using QuantConnect.Orders.Fees;
    using QuantConnect.Orders.Fills;
    using QuantConnect.Orders.OptionExercise;
    using QuantConnect.Orders.Slippage;
    using QuantConnect.Orders.TimeInForces;
    using QuantConnect.Python;
    using QuantConnect.Scheduling;
    using QuantConnect.Securities;
    using QuantConnect.Securities.Equity;
    using QuantConnect.Securities.Future;
    using QuantConnect.Securities.Option;
    using QuantConnect.Securities.Positions;
    using QuantConnect.Securities.Forex;
    using QuantConnect.Securities.Crypto;
    using QuantConnect.Securities.CryptoFuture;
    using QuantConnect.Securities.Interfaces;
    using QuantConnect.Securities.Volatility;
    using QuantConnect.Storage;
    using QuantConnect.Statistics;
    using QCAlgorithmFramework = QuantConnect.Algorithm.QCAlgorithm;
    using QCAlgorithmFrameworkBridge = QuantConnect.Algorithm.QCAlgorithm;
#endregion
namespace QuantConnect.Algorithm.CSharp
{
    public class $CLASS_NAME$ : QCAlgorithm
    {

        public override void Initialize()
        {
            // Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data
            SetStartDate(2013, 10, 7); // Set Start Date
            SetEndDate(2013, 10, 11); // Set Start Date
            SetCash(100000);             //Set Strategy Cash

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
#region imports
    using System;
    using System.Collections;
    using System.Collections.Generic;
    using System.Linq;
    using System.Globalization;
    using System.Drawing;
    using QuantConnect;
    using QuantConnect.Algorithm.Framework;
    using QuantConnect.Algorithm.Framework.Selection;
    using QuantConnect.Algorithm.Framework.Alphas;
    using QuantConnect.Algorithm.Framework.Portfolio;
    using QuantConnect.Algorithm.Framework.Portfolio.SignalExports;
    using QuantConnect.Algorithm.Framework.Execution;
    using QuantConnect.Algorithm.Framework.Risk;
    using QuantConnect.Api;
    using QuantConnect.Parameters;
    using QuantConnect.Benchmarks;
    using QuantConnect.Brokerages;
    using QuantConnect.Configuration;
    using QuantConnect.Util;
    using QuantConnect.Interfaces;
    using QuantConnect.Algorithm;
    using QuantConnect.Indicators;
    using QuantConnect.Data;
    using QuantConnect.Data.Auxiliary;
    using QuantConnect.Data.Consolidators;
    using QuantConnect.Data.Custom;
    using QuantConnect.Data.Custom.IconicTypes;
    using QuantConnect.DataSource;
    using QuantConnect.Data.Fundamental;
    using QuantConnect.Data.Market;
    using QuantConnect.Data.Shortable;
    using QuantConnect.Data.UniverseSelection;
    using QuantConnect.Notifications;
    using QuantConnect.Orders;
    using QuantConnect.Orders.Fees;
    using QuantConnect.Orders.Fills;
    using QuantConnect.Orders.OptionExercise;
    using QuantConnect.Orders.Slippage;
    using QuantConnect.Orders.TimeInForces;
    using QuantConnect.Python;
    using QuantConnect.Scheduling;
    using QuantConnect.Securities;
    using QuantConnect.Securities.Equity;
    using QuantConnect.Securities.Future;
    using QuantConnect.Securities.Option;
    using QuantConnect.Securities.Positions;
    using QuantConnect.Securities.Forex;
    using QuantConnect.Securities.Crypto;
    using QuantConnect.Securities.CryptoFuture;
    using QuantConnect.Securities.Interfaces;
    using QuantConnect.Securities.Volatility;
    using QuantConnect.Storage;
    using QuantConnect.Statistics;
    using QCAlgorithmFramework = QuantConnect.Algorithm.QCAlgorithm;
    using QCAlgorithmFrameworkBridge = QuantConnect.Algorithm.QCAlgorithm;
#endregion


namespace QuantConnect
{
    /// <summary>
    /// Template Library Class
    ///
    /// Library classes are snippets of code you can reuse between projects. They are added to projects on compile. This can be useful for reusing
    /// indicators, math components, risk modules etc. If you use a custom namespace make sure you add the correct using statement to the
    /// algorithm.
    /// </summary>
    public static class $CLASS_NAME$
    {
        /*
         * To use this library; add its namespace at the top of the page:
         * using QuantConnect
         *
         * Then use the static class:
         * var x = $CLASS_NAME$.Add(1, 5);
         * Console.Out.WriteLine(x);
         */

        public static int Add(int a, int b)
        {
            return a + b;
        }

        public static int Subtract(int a, int b)
        {
            return a - b;
        }

        public static int Divide(int a, int b){
            return a / b;
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
                "// For more information see https://www.quantconnect.com/docs/v2/our-platform/research/getting-started\\n",
                "#load \\"../QuantConnect.csx\\"\\n",
                "\\n",
                "using QuantConnect;\\n",
                "using QuantConnect.Data;\\n",
                "using QuantConnect.Research;\\n",
                "using QuantConnect.Algorithm;\\n",
                "\\n",
                "var qb = new QuantBook();\\n",
                "// Locally Lean installs free sample data, to download more data please visit https://www.quantconnect.com/docs/v2/lean-cli/datasets/downloading-data \\n",
                "qb.SetStartDate(2013, 10, 11);\\n",
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

def _not_identifier_char(text):
    problematic_char = text[-1]
    for i in range(1, len(text)):
        substring = text[:i]
        if not substring.isidentifier():
            problematic_char = substring[-1]
            break
    return problematic_char

@lean.command(cls=LeanCommand, name="project-create", aliases=["create-project"])
@argument("name", type=str)
@option("--language", "-l",
              type=Choice(container.cli_config_manager.default_language.allowed_values, case_sensitive=False),
              help="The language of the project to create")
def create_project(name: str, language: str) -> None:
    """Create a new project containing starter code.

    If NAME is a path containing subdirectories those will be created automatically.

    The default language can be set using `lean config set default-language python/csharp`.
    """
    cli_config_manager = container.cli_config_manager

    language = language if language is not None else cli_config_manager.default_language.get_value()
    if language is None:
        raise MoreInfoError(
            "Please specify a language with --language or set the default language using `lean config set default-language python/csharp`",
            "https://www.lean.io/docs/v2/lean-cli/projects/project-management")

    full_path = Path.cwd() / name
    try:
        cli_root_dir = container.lean_config_manager.get_cli_root_directory()
        relative_path = full_path.relative_to(cli_root_dir).as_posix()
    except MoreInfoError:
        relative_path = name

    if not container.path_manager.is_cli_path_valid(full_path) or not container.path_manager.is_name_valid(relative_path):
        raise MoreInfoError(f"Invalid project name. Can only contain letters, numbers & spaces. Can not start with empty char ' ' or be a reserved name [ {', '.join(reserved_names)} ]",
                         "https://www.lean.io/docs/v2/lean-cli/key-concepts/troubleshooting#02-Common-Errors")

    is_library_project = False
    try:
        library_dir = container.lean_config_manager.get_cli_root_directory() / "Library"
        is_library_project = library_dir in full_path.parents
        if is_library_project:
            # Make sure we always use the same casing 'Library' for the library directory
            full_path = library_dir / full_path.relative_to(library_dir)
    except:
        # get_cli_root_directory() raises an error if there is no such directory
        pass

    id_name = full_path.name
    if is_library_project and language == "python" and not id_name.isidentifier():
        problematic_char = _not_identifier_char(id_name)
        raise RuntimeError(
            f"""'{id_name}' is not a valid Python identifier, which is required for Python library projects to be importable.
Please remove the character '{problematic_char}' and retry""")

    if full_path.exists():
        raise RuntimeError(f"A project named '{name}' already exists, please choose a different name")
    else:
        project_manager = container.project_manager
        project_manager.create_new_project(full_path, QCLanguage.Python if language == "python" else QCLanguage.CSharp)

    class_name = convert_to_class_name(full_path)

    if language == "python":
        main_name = "main.py" if not is_library_project else "Library.py"
        research_name = "research.ipynb"
        main_content = DEFAULT_PYTHON_MAIN if not is_library_project else LIBRARY_PYTHON_MAIN
    else:
        main_name = "Main.cs" if not is_library_project else "Library.cs"
        research_name = "Research.ipynb"
        main_content = DEFAULT_CSHARP_MAIN if not is_library_project else LIBRARY_CSHARP_MAIN

    with (full_path / main_name).open("w+", encoding="utf-8") as file:
        file.write(main_content.replace("$CLASS_NAME$", class_name).replace("$PROJECT_NAME$", full_path.name))

    if not is_library_project:
        with (full_path / research_name).open("w+", encoding="utf-8") as file:
            file.write(DEFAULT_PYTHON_NOTEBOOK if language == "python" else DEFAULT_CSHARP_NOTEBOOK)

    if language == "csharp":
        project_manager = container.project_manager
        project_csproj_file = project_manager.get_csproj_file_path(full_path)
        original_csproj_content = project_csproj_file.read_text(encoding="utf-8")
        project_manager.try_restore_csharp_project(project_csproj_file, original_csproj_content, False)

    logger = container.logger
    logger.info(f"Successfully created {'Python' if language == 'python' else 'C#'} project '{name}'")
