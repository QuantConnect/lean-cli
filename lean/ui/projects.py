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

from dataclasses import dataclass
from datetime import datetime
from os import walk
from pathlib import Path
from typing import List, Optional

from lean.constants import PROJECT_CONFIG_FILE_NAME
from lean.models.api import QCProject

LANGUAGE_LABELS = {"Python": "Py", "CSharp": "C#", "Py": "Py", "C#": "C#"}


@dataclass
class UIProject:
    """A project as shown in the UI, which may exist locally, in the cloud, or both."""

    name: str
    path: Optional[Path] = None
    cloud_id: Optional[int] = None
    language: str = ""
    description: str = ""
    modified: Optional[datetime] = None

    @property
    def is_local(self) -> bool:
        return self.path is not None

    @property
    def is_cloud(self) -> bool:
        return self.cloud_id is not None

    @property
    def is_library(self) -> bool:
        return self.name.split("/")[0] == "Library"

    @property
    def location(self) -> str:
        if self.is_local and self.is_cloud:
            return "synced"
        return "local" if self.is_local else "cloud"


def discover_local_projects(root: Path, skip_dirs: Optional[List[Path]] = None) -> List[UIProject]:
    """Finds all projects under the CLI root directory.

    A project is a directory containing a project config file. Project directories are not searched further,
    so backtest and live output folders inside a project are never mistaken for projects.

    :param root: the CLI root directory, the one containing the Lean config file
    :param skip_dirs: directories not to search, like the data directory
    :return: the local projects, sorted by name
    """
    from lean.container import container

    skip = {str(p.resolve()) for p in (skip_dirs or [])}
    projects = []

    for current, dirs, files in walk(root):
        current_path = Path(current)
        if PROJECT_CONFIG_FILE_NAME in files and current_path != root:
            config = container.project_config_manager.get_project_config(current_path)
            projects.append(UIProject(
                name=current_path.relative_to(root).as_posix(),
                path=current_path,
                cloud_id=config.get("cloud-id"),
                language=LANGUAGE_LABELS.get(config.get("algorithm-language", ""), ""),
                description=config.get("description", ""),
                modified=datetime.fromtimestamp(current_path.stat().st_mtime)
            ))
            dirs.clear()
            continue

        dirs[:] = sorted(d for d in dirs
                         if not d.startswith(".") and str((current_path / d).resolve()) not in skip)

    return sorted(projects, key=lambda p: p.name.casefold())


def merge_cloud_projects(local_projects: List[UIProject], cloud_projects: List[QCProject]) -> List[UIProject]:
    """Combines local projects with the projects in the cloud.

    Local projects are matched to cloud projects by their cloud id, cloud projects without a local copy are added.

    :param local_projects: the projects found on disk
    :param cloud_projects: the projects of the working organization in the cloud
    :return: all projects, sorted by name
    """
    by_cloud_id = {p.cloud_id: p for p in local_projects if p.cloud_id is not None}
    merged = list(local_projects)

    for cloud_project in cloud_projects:
        local_project = by_cloud_id.get(cloud_project.projectId)
        if local_project is not None:
            local_project.description = cloud_project.description or local_project.description
            local_project.modified = cloud_project.modified
            continue

        merged.append(UIProject(
            name=cloud_project.name,
            cloud_id=cloud_project.projectId,
            language=LANGUAGE_LABELS.get(cloud_project.language.value, cloud_project.language.value),
            description=cloud_project.description,
            modified=cloud_project.modified
        ))

    # Cloud projects whose id is stored locally but no longer exist are shown as local only
    cloud_ids = {p.projectId for p in cloud_projects}
    for project in merged:
        if project.is_local and project.cloud_id not in cloud_ids:
            project.cloud_id = None

    return sorted(merged, key=lambda p: p.name.casefold())


def filter_projects(projects: List[UIProject], query: str) -> List[UIProject]:
    """Returns the projects whose name contains every word of the query, ignoring case."""
    words = query.casefold().split()
    return [p for p in projects if all(w in p.name.casefold() for w in words)]


def is_logged_in() -> bool:
    """Returns whether credentials are stored, without contacting the API."""
    from lean.container import container

    cli_config_manager = container.cli_config_manager
    return cli_config_manager.user_id.get_value() is not None and cli_config_manager.api_token.get_value() is not None


def fetch_cloud_projects() -> List[QCProject]:
    """Returns the projects of the working organization in the cloud. Makes a blocking API request."""
    from lean.container import container

    organization_id = container.organization_manager.try_get_working_organization_id()
    return container.api_client.projects.get_all(organization_id)
