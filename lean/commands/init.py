import shutil
import tempfile
import zipfile
from pathlib import Path

import click

from lean.click import LeanCommand
from lean.container import container


@click.command(cls=LeanCommand)
def init() -> None:
    """Bootstrap a Lean CLI project."""
    current_dir = Path.cwd()
    data_dir = current_dir / container.config()["default_data_directory_name"]
    lean_config_path = current_dir / container.config()["default_lean_config_file_name"]

    # Abort if one of the files we are going to create already exists to prevent us from overriding existing files
    for path in [data_dir, lean_config_path]:
        if path.exists():
            relative_path = path.relative_to(current_dir)
            raise RuntimeError(f"{relative_path} already exists, please run this command in an empty directory")

    logger = container.logger()

    # Warn the user if the current directory is not empty
    if next(current_dir.iterdir(), None) is not None:
        logger.info("This command will bootstrap a Lean CLI project in the current directory")
        click.confirm("The current directory is not empty, continue?", default=False, abort=True)

    logger.info("Downloading latest sample data from the Lean repository...")

    tmp_directory = Path(tempfile.mkdtemp())
    http_client = container.http_client()

    # We download the entire Lean repository and extract the data and the launcher's config file
    # GitHub doesn't allow downloading a specific directory
    # Since we need ~80% of the total repository in terms of file size this shouldn't be too big of a problem
    http_client.download_file("https://github.com/QuantConnect/Lean/archive/master.zip", tmp_directory / "master.zip")
    with zipfile.ZipFile(tmp_directory / "master.zip") as zip_file:
        zip_file.extractall(tmp_directory / "master")

    # Create the data directory
    shutil.copytree(tmp_directory / "master" / "Lean-master" / "Data", data_dir)

    # Create the config file
    lean_config_manager = container.lean_config_manager()
    config = (tmp_directory / "master" / "Lean-master" / "Launcher" / "config.json").read_text()
    config = lean_config_manager.clean_lean_config(config)

    with lean_config_path.open("w+") as file:
        file.write(config)

    # Prompt for some general configuration if not set yet
    cli_config_manager = container.cli_config_manager()
    if cli_config_manager.default_language.get_value() is None:
        default_language = click.prompt("What should the default language for new projects be?",
                                        type=click.Choice(cli_config_manager.default_language.allowed_values))
        cli_config_manager.default_language.set_value(default_language)

    logger.info(f"""
Successfully bootstrapped your Lean CLI project!

The following structure has been created:
- {lean_config_path} contains the configuration used when running the LEAN engine locally
- {data_dir} contains the data that is used when running the LEAN engine locally

Here are some commands to get you going:
- Run `lean create-project "My Project"` to create a new project with starter code
- Run `lean backtest "My Project"` to backtest a project locally with the data in {data_dir}
""".strip())
