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

import webbrowser
from pathlib import Path
from random import choice
from typing import Optional

import click
from rich import box
from rich.table import Table
from rich.text import Text

from lean.click import LeanCommand
from lean.container import container
from lean.models.api import QCBacktest

# Name generation logic is based on
# https://github.com/QuantConnect/Lean/blob/5034c28c2efb4691a148b2c4a59f1c7ceb5f3b7e/VisualStudioPlugin/BacktestNameProvider.cs

VERBS = ["Determined", "Pensive", "Adaptable", "Calculating", "Logical", "Energetic", "Creative", "Smooth", "Calm",
         "Hyper-Active", "Measured", "Fat", "Emotional", "Crying", "Jumping", "Swimming", "Crawling", "Dancing",
         "Focused", "Well Dressed", "Retrospective", "Hipster", "Square", "Upgraded", "Ugly", "Casual", "Formal",
         "Geeky", "Virtual", "Muscular", "Alert", "Sleepy"]

COLORS = ["Red", "Red-Orange", "Orange", "Yellow", "Tan", "Yellow-Green", "Yellow-Green", "Fluorescent Orange",
          "Apricot", "Green", "Fluorescent Pink", "Sky Blue", "Fluorescent Yellow", "Asparagus", "Blue", "Violet",
          "Light Brown", "Brown", "Magenta", "Black"]

ANIMALS = ["Horse", "Zebra", "Whale", "Tapir", "Barracuda", "Cow", "Cat", "Wolf", "Hamster", "Monkey", "Pelican",
           "Snake", "Albatross", "Viper", "Guanaco", "Anguilline", "Badger", "Dogfish", "Duck", "Butterfly", "Gaur",
           "Rat", "Termite", "Eagle", "Dinosaur", "Pig", "Seahorse", "Hornet", "Koala", "Hippopotamus", "Cormorant",
           "Jackal", "Rhinoceros", "Panda", "Elephant", "Penguin", "Beaver", "Hyena", "Parrot", "Crocodile", "Baboon",
           "Pony", "Chinchilla", "Fox", "Lion", "Mosquito", "Cobra", "Mule", "Coyote", "Alligator", "Pigeon",
           "Antelope", "Goat", "Falcon", "Owlet", "Llama", "Gull", "Chicken", "Caterpillar", "Giraffe", "Rabbit",
           "Flamingo", "Caribou", "Goshawk", "Galago", "Bee", "Jellyfish", "Buffalo", "Salmon", "Bison", "Dolphin",
           "Jaguar", "Dog", "Armadillo", "Gorilla", "Alpaca", "Kangaroo", "Dragonfly", "Salamander", "Owl", "Bat",
           "Sheep", "Frog", "Chimpanzee", "Bull", "Scorpion", "Lemur", "Camel", "Leopard", "Fish", "Donkey", "Manatee",
           "Shark", "Bear", "kitten", "Fly", "Ant", "Sardine"]


def _log_backtest_stats(backtest: QCBacktest) -> None:
    """Logs the results of the backtest in a nice table.

    :param backtest: the backtest to log the results of
    """
    stats = []

    for key, value in backtest.runtimeStatistics.items():
        stats.append(key)

        if "-" in value:
            stats.append(Text.from_markup(f"[red]{value}[/red]"))
        elif any(char.isdigit() and int(char) > 0 for char in value):
            stats.append(Text.from_markup(f"[green]{value}[/green]"))
        else:
            stats.append(value)

    if len(stats) % 4 != 0:
        stats.extend(["", ""])

    end_of_first_section = len(stats)

    for key, value in backtest.statistics.items():
        stats.extend([key, value])

    if len(stats) % 4 != 0:
        stats.extend(["", ""])

    table = Table(box=box.SQUARE)
    table.add_column("Statistic")
    table.add_column("Value")
    table.add_column("Statistic")
    table.add_column("Value")

    for i in range(int(len(stats) / 4)):
        start = i * 4
        end = (i + 1) * 4
        table.add_row(*stats[start:end], end_section=end_of_first_section == end)

    logger = container.logger()
    logger.info(table)


@click.command(cls=LeanCommand)
@click.argument("project", type=str)
@click.option("--name", type=str, help="The name of the backtest (a random one is generated if not specified)")
@click.option("--push",
              is_flag=True,
              default=False,
              help="Push local modifications to the cloud before running the backtest")
@click.option("--open", "open_browser",
              is_flag=True,
              default=False,
              help="Automatically open the browser with the results when the backtest is finished")
def backtest(project: str, name: Optional[str], push: bool, open_browser: bool) -> None:
    """Run a backtest in the cloud.

    PROJECT should be the name or id of a cloud project.

    If the project that has to be backtested has been pulled to the local drive
    with `lean cloud pull` it is possible to use the --push option to push local
    modifications to the cloud before running the backtest.
    """
    logger = container.logger()

    api_client = container.api_client()
    all_projects = api_client.projects.get_all()

    for p in all_projects:
        if str(p.projectId) == project or p.name == project:
            cloud_project = p
            break
    else:
        raise RuntimeError("No project with the given name or id exists in the cloud")

    if push:
        local_path = Path.cwd() / cloud_project.name
        if local_path.exists():
            push_manager = container.push_manager()
            push_manager.push_projects([local_path])
        else:
            logger.info(f"'{cloud_project.name}' does not exist locally, not pushing anything")

    if name is None:
        name = f"{choice(VERBS)} {choice(COLORS)} {choice(ANIMALS)}"

    cloud_runner = container.cloud_runner()
    finished_backtest = cloud_runner.run_backtest(cloud_project, name)

    _log_backtest_stats(finished_backtest)

    logger.info(f"Backtest id: {finished_backtest.backtestId}")
    logger.info(f"Backtest name: {finished_backtest.name}")
    logger.info(f"Backtest url: {finished_backtest.get_url()}")

    if finished_backtest.error is not None:
        error = finished_backtest.stacktrace or finished_backtest.error

        logger.error("An error occurred during this backtest:")
        logger.error(error)

        # Don't open the results in the browser if the error happened during initialization
        # In the browser the logs won't show these errors, you'll just get empty charts and empty logs
        if error.startswith("During the algorithm initialization, the following exception has occurred:"):
            open_browser = False

    if open_browser:
        webbrowser.open(finished_backtest.get_url())
