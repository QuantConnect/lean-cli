# # QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# # Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.


# from pathlib import Path
# import click
# from lean.click import LeanCommand, PathParameter
# from lean.container import container
# from lean.components.util.logger import Logger
# from lean.constants import COMMANDS_FILE_PATH


# @click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
# @click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
# @click.option("--environment",
#               type=str,
#               help="The environment to use")
# @click.option("--environment",
#               type=str,
#               help="The environment to use")
# @click.option("--environment",
#               type=str,
#               help="The environment to use")
# def liquidate(project: Path,
#             brokerage: Optional[str],
#             data_feed: Optional[str],
#             data_feed: Optional[str]) -> None:
#     """
#     Liquidate .
#     """
    
#     docker_container_name = container.output_config_manager().get_container_name(project)
#     data = {
#         "command": "stop",
#     }
#     Logger.info(f"Sending command to container {docker_container_name}")
#     try:
#         container.docker_manager().write_to_file(docker_container_name, COMMANDS_FILE_PATH, data)
#     except Exception as e:
#         Logger.error(f"Failed to execute the command: {e}")



