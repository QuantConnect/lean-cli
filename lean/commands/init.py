import re
import tempfile
import zipfile
from pathlib import Path

import click
import requests
from tqdm import tqdm

from lean.constants import DEFAULT_DATA_DIR, DEFAULT_CONFIG_FILE


def remove_section_from_config(config: str, json_key: str) -> str:
    """Remove a section from Lean's launcher config.

    Lean's launcher config contains some configurable options that the CLI is able
    to set automatically based on the command that is being ran.
    This function removes those sections from the config.

    For example, given the following config:
    {
        // Doc 1
        "key1": "value1",

        // Doc 2
        "key2": "value2"
    }

    Calling remove_section_from_config(config, "key1") would return the following:
    {
        // Doc 2
        "key2": "value2"
    }

    This function is implemented by doing string manipulation because the JSON contains comments.
    If we were to parse it as JSON, we would have to remove the comments which we don't want to do.

    :param config: the config to remove the section containing the json_key from
    :param json_key: a json key in the section to remove
    :return: a new string containing the config without the section containing the specified json key
    """
    sections = re.split(r"\n\s*\n", config)
    sections = [section for section in sections if f"\"{json_key}\": " not in section]
    return "\n\n".join(sections)


@click.command()
def init() -> None:
    """Bootstrap a Lean CLI project."""
    current_dir = Path.cwd()
    data_dir = current_dir / DEFAULT_DATA_DIR
    lean_config_path = current_dir / DEFAULT_CONFIG_FILE

    # Abort if one of the files we are going to create already exists to prevent us from overriding existing files
    for path in [data_dir, lean_config_path]:
        if path.exists():
            relative_path = path.relative_to(current_dir)
            raise click.ClickException(f"{relative_path} already exists, please run this command in an empty directory")

    # Warn the user if the current directory is not empty
    if next(current_dir.iterdir(), None) is not None:
        click.echo("This command will bootstrap a Lean CLI project in the current directory")
        click.confirm("The current directory is not empty, continue?", default=False, abort=True)

    click.echo("Downloading latest sample data from the Lean repository...")

    # We download the entire Lean repository and extract the data and the launcher's config file
    # GitHub doesn't allow downloading a specific directory
    # Since we extract ~80% of the total repository in terms of file size, this shouldn't be too big of a problem
    lean_zip_response = requests.get("https://github.com/QuantConnect/Lean/archive/master.zip", stream=True)
    total_size_bytes = int(lean_zip_response.headers.get("content-length", 0))

    # Sometimes content length isn't set, don't show a progress bar in that case
    if total_size_bytes > 0:
        progress_bar = tqdm(total=total_size_bytes, bar_format="{l_bar}{bar}", ncols=50)
    else:
        progress_bar = None

    with tempfile.TemporaryFile() as lean_zip_file:
        for chunk in lean_zip_response.iter_content(chunk_size=128):
            lean_zip_file.write(chunk)

            if progress_bar is not None:
                progress_bar.update(len(chunk))

        if progress_bar is not None:
            progress_bar.close()

        with zipfile.ZipFile(lean_zip_file) as zip_file:
            # Extract the Data directory
            for file_info in [x for x in zip_file.filelist if not x.is_dir() and "Lean-master/Data/" in x.filename]:
                target_location = data_dir / file_info.filename.replace("Lean-master/Data/", "")

                if not target_location.parent.exists():
                    target_location.parent.mkdir(parents=True)

                with open(target_location, "wb") as target_file:
                    target_file.write(zip_file.read(file_info))

            # Extract the launcher config
            config = zip_file.read("Lean-master/Launcher/config.json").decode("utf-8")

            # Remove the config sections which the CLI can set automatically
            for key in ["environment",
                        "algorithm-type-name", "algorithm-language", "algorithm-location",
                        "debugging", "debugging-method",
                        "composer-dll-directory",
                        "job-user-id", "api-access-token"]:
                config = remove_section_from_config(config, key)

            # Update the data-folder configuration
            config = config.replace('"data-folder": "../../../Data/"', f'"data-folder": "{DEFAULT_DATA_DIR}"')

            # Save the modified config
            with open(lean_config_path, "w+") as file:
                file.write(config)

    click.echo("Successfully bootstrapped your Lean CLI project!")
    click.echo()
    click.echo("The following structure has been created:")
    click.echo(f"- {DEFAULT_CONFIG_FILE} contains the configuration used when running the LEAN engine locally")
    click.echo(f"- {DEFAULT_DATA_DIR}/ contains the data that is used when running the LEAN engine locally")
    click.echo()
    click.echo("Here are some commands to get you going:")
    click.echo('- Run `lean create-project --language python "My Project"` to create a new project with starter code')
    click.echo(f'- Run `lean backtest "My Project"` to backtest a project locally with the data in {DEFAULT_DATA_DIR}/')
