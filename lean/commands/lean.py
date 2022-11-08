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

from click import group, version_option

from lean import __version__
from lean.components.util.click_aliased_command_group import AliasedCommandGroup
from lean.container import container
from lean.models.errors import MoreInfoError


@group(cls=AliasedCommandGroup)
@version_option(__version__)
def lean() -> None:
    """The Lean CLI by QuantConnect."""
    # This method is used as the command group for all `lean <command>` commands

    # Here we check whether `lean init` has already been called and this is an old CLI folder
    # before passing through the actual invoked command, to make sure this is not an old CLI folder.
    # TODO: This check is to be removed once some time has passed after
    #  the "one cli folder per organization" change is settled

    lean_config_manager = container.lean_config_manager
    try:
        lean_config_manager.get_lean_config()
    except MoreInfoError:
        # There is no config, proceed in case `lean init` is being invoked
        return

    # `lean init` was already called. Let's check whether this is an old Lean CLI directory
    organization_manager = container.organization_manager
    if organization_manager.get_working_organization_id() is None:
        raise RuntimeError(
            "This is an old Lean CLI root folder.\n"
            "From now on, a Lean CLI root folder must be created for each organization for improved usability.\n"
            "For each organization you'd like to use with the CLI, please create a new folder and run `lean init`.")
