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
from lean.container import container

logger = container.logger()


@click.command(cls=LeanCommand)
@click.option("--live",'mode',flag_value="live",help="get latest live log")
@click.option("--backtest",'mode',flag_value="backtests",help="get latest backtests log")
@click.option("--optimization",'mode',flag_value="optimizations",help="get latest optimization log")
@click.option("--project_path",type=PathParameter(exists=True,dir_okay=True,file_okay=False),
help="get log from project path Ex: <Project>/<mode>/<datetime> :: 'Python Project/live/2020-01-01_00-00-00'")
@click.option("--project",type=str,help="get latest log from Project Name")
def logs(mode:str,project_path:Path,project:str,print_n_lines=5):
    """Logs command that ouputs log based on the type such as Live / Backtesting / Optimizations

    Args:
        mode (str): [description]
        project_path (PathParameter): [description]
    """
    if mode is None and project_path is None:
        logger.info("--live or --backtest or --optimization flags are not provided. Defaulting to backtest.")
        mode="backtests"
    if project_path is None:
        if project is None:
            mode_log_files = list(Path.cwd().rglob(f"{mode}/*/log.txt"))
        else:
            if Path(project).exists():
                mode_log_files = list(Path.cwd().rglob(f"{project}/{mode}/*/log.txt"))
            else:
                raise NotADirectoryError(f"{project} Project not created. Please create using lean create-project {project}.")
        if len(mode_log_files) == 0:
                raise ValueError(
                    f"Could not find a recent {mode} log file, see if you have run project in {mode} mode"
                )
        mode_log_file = sorted(mode_log_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
        project_path = mode_log_file.parent
    else:
        mode_log_file = project_path/"log.txt"
    if not mode_log_file.exists():
        raise FileNotFoundError(f"Cannot find log file for {project_path}. Please rerun the project with {mode} mode.")
    with open(mode_log_file) as file:
        buffer = []
        full_flag=False
        for line in file.readlines():
            if full_flag!=True:
                buffer.append(line)
                if len(buffer)>=print_n_lines:
                    print("".join(buffer),end="")
                    buffer.clear()
                    input_char = input("Press Enter to print next set of lines or Press a and Enter for printing full log file.")
                    if input_char=="a":
                        full_flag=True
            else:
                print(line,end="")

        print("".join(buffer))
        logger.info("End of the Log!")

            
    
    