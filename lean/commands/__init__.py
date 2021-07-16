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

from lean import __version__
from lean.commands.backtest import backtest
from lean.commands.build import build
from lean.commands.cloud import cloud
from lean.commands.config import config
from lean.commands.create_project import create_project
from lean.commands.data import data
from lean.commands.gui import gui
from lean.commands.init import init
from lean.commands.library import library
from lean.commands.live import live
from lean.commands.login import login
from lean.commands.logout import logout
from lean.commands.optimize import optimize
from lean.commands.report import report
from lean.commands.research import research
from lean.commands.whoami import whoami


@click.group()
@click.version_option(__version__)
def lean() -> None:
    """The Lean CLI by QuantConnect."""
    # This method is intentionally empty
    # It is used as the command group for all `lean <command>` commands
    pass


lean.add_command(config)
lean.add_command(cloud)
lean.add_command(data)
lean.add_command(library)
lean.add_command(gui)

lean.add_command(login)
lean.add_command(logout)
lean.add_command(whoami)
lean.add_command(init)
lean.add_command(create_project)
lean.add_command(backtest)
lean.add_command(optimize)
lean.add_command(research)
lean.add_command(report)
lean.add_command(live)
lean.add_command(build)
