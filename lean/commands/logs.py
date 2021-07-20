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
from pathlib import Path
from lean.click import LeanCommand,PathParameter
from lean.models.errors import MoreInfoError

@click.command(cls=LeanCommand)
@click.option("--live",'mode',flag_value="live",help="Ouputs Live Logs")
@click.option("--backtest",'mode',flag_value="backtests",help="Ouputs Backtests Logs")
@click.option("--optimization",'mode',flag_value="optimizations",help="Ouputs Backtests Logs")
@click.option("--project_path",type=PathParameter(exists=True,dir_okay=True,file_okay=False),help="Path to Project")
def logs(mode:str,project_path:Path):
    """Logs command that ouputs log based on the type such as Live / Backtesting / Optimizations

    Args:
        mode (str): [description]
        project_path (PathParameter): [description]
    """
    if mode is None:
        raise ValueError("Mode is not given. either one of the flags. --live, --backtest, --optimization")
    if project_path is None:
        mode_log_files = list(Path.cwd().rglob(f"{mode}/*/log.txt"))
        if len(mode_log_files) == 0:
            raise MoreInfoError(
                f"Could not find a recent {mode} log file, see if you have run any project in {mode} mode",
                "https://www.lean.io/docs/lean-cli/tutorials/generating-reports"
            )
        mode_log_file = sorted(mode_log_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
        project_path = mode_log_file.parent
    else:
        mode_log_file = project_path/"log.txt"
    if not mode_log_file.exists():
        raise FileNotFoundError(f"Cannot find log file for {project_path}. Please rerun the project with {mode} mode.")
    with open(mode_log_file) as file:
        for line in file.readlines():
            print(line)
            input("Press Enter to print next line")
            
    
    