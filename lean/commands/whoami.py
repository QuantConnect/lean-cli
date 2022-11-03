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

from click import command

from lean.click import LeanCommand
from lean.container import container
from lean.models.errors import AuthenticationError


@command(cls=LeanCommand)
def whoami() -> None:
    """Display who is logged in."""
    logger = container.logger
    api_client = container.api_client
    cli_config_manager = container.cli_config_manager

    if cli_config_manager.user_id.get_value() is not None and cli_config_manager.api_token.get_value() is not None:
        try:
            organizations = api_client.organizations.get_all()
            logged_in = True
        except AuthenticationError:
            logged_in = False
    else:
        logged_in = False

    if not logged_in:
        logger.info("You are not logged in")
        return

    personal_organization_id = next(o.id for o in organizations if o.ownerName == "You")
    personal_organization = api_client.organizations.get(personal_organization_id)
    member = next(m for m in personal_organization.members if m.isAdmin)

    logger.info(f"You are logged in as {member.name} ({member.email})")
