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
from typing import Optional

import click

from lean.click import LeanCommand, PathParameter
from lean.constants import PROJECT_CONFIG_FILE_NAME
from lean.container import container


@click.command(cls=LeanCommand)
@click.option("--project",
              type=PathParameter(exists=True, file_okay=False, dir_okay=True),
              help="Path to the local project to push (all local projects if not specified)")
def push(project: Optional[Path]) -> None:
    """Push local projects to QuantConnect.

    This command overrides the content of cloud files with the content of their respective local counterparts.

    This command will not delete cloud files which don't have a local counterpart.
    """
    # Parse which projects need to be pushed
    if project is not None:
        project_config_manager = container.project_config_manager()
        if not project_config_manager.get_project_config(project).file.exists():
            raise RuntimeError(f"'{project}' is not a Lean project")

        projects_to_push = [project]
    else:
        projects_to_push = [p.parent for p in Path.cwd().rglob(PROJECT_CONFIG_FILE_NAME)]

    push_manager = container.push_manager()
    push_manager.push_projects(projects_to_push)
