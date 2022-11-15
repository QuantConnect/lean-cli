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

from json import dumps
from typing import Dict, Any
from lean.container import container
from pathlib import Path

docker_manager = container.docker_manager
project_manager = container.project_manager
lean_runner = container.lean_runner
temp_manager = container.temp_manager
project_config_manager = container.project_config_manager
cli_config_manager = container.cli_config_manager
logger = container.logger


def get_success() -> Dict[str, Any]:
    """Compiles success message.

    :return: success object as json dump.
    """
    return dumps({
        "eType": "BuildSuccess",
    })


def get_errors(algorithm_type: str, message: str, color_coding_required: bool = True,
                                        warning_required: bool = True) -> Dict[str, Any]:
    """Compiles error message based on given input

    :param algorithm_type: type of algorithm: "python" or "csharp".
    :param message: message from which errors needs to be formatted.
    :return: error object as json dump.
    """
    errors = []
    if algorithm_type == "csharp":
        errors.extend(_parse_csharp_errors(message, color_coding_required, warning_required))
    elif algorithm_type == "python":
        errors.extend(_parse_python_errors(message, color_coding_required))

    return dumps({
        "eType": "BuildError",
        "aErrors": errors,
    })


def redirect_stdout_of_subprocess(method_name_to_run, *args, **kwargs) -> tuple:
    """ It captures the stdout of the method given to run.

    :param method_name_to_run: name of the method to run
    :return: result of the method and the stdout of the process
    """
    from io import StringIO
    from contextlib import redirect_stdout
    f = StringIO()
    with redirect_stdout(f):
        result = method_name_to_run(*args, **kwargs)
    stdout = f.getvalue()
    return (result, stdout)


def compile() -> None:
    """This is a utility function that is used by the vscode plugin project.
    """

    # We need to print the stdout of the docker run command from here,
    # so that it can be picked up by the subprocess that is being
    # called by the vscode plugin.
    compile_result, stdout = redirect_stdout_of_subprocess(_compile)
    if compile_result["result"]:
        processed_output = get_success()
    else:
        processed_output = get_errors(compile_result["algorithmType"], stdout, False, False)
    logger.info(processed_output)


def _compile() -> Dict[str, Any]:
    """
    This function compile c# and python project files.
    """
    from sys import argv

    message = {
        "result": False,
        "algorithmType": "",
    }

    project_dir = Path(argv[-1])
    if not project_dir.exists():
        raise(f"Project directory {project_dir} does not exist")

    algorithm_file = project_manager.find_algorithm_file(project_dir)
    message["algorithmType"] = "python" if algorithm_file.name.endswith(".py") else "csharp"

    # The dict containing all options passed to `docker run`
    # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
    run_options: Dict[str, Any] = {
        "commands": [],
        "environment": {},
        "mounts": [],
        "volumes": {}
    }
    lean_runner.mount_project_and_library_directories(project_dir, run_options)
    lean_runner.setup_language_specific_run_options(run_options, project_dir, algorithm_file, False, False)

    project_config = project_config_manager.get_project_config(project_dir)
    engine_image = cli_config_manager.get_engine_image(
        project_config.get("engine-image", None))

    message["result"] = docker_manager.run_image(engine_image, **run_options)
    temp_manager.delete_temporary_directories_when_done = False
    return message

def _parse_csharp_errors(csharp_output: str, color_coding_required: bool, warning_required: bool) -> list:
    from re import findall
    errors = []

    try:
        relevant_output = csharp_output[csharp_output.index("Build FAILED."):]
        for match in findall(r"(.*)\((\d+),(\d+)\): (error|warning) ([a-zA-Z0-9]+): ([^[]+) ", relevant_output):
            if color_coding_required:
                if match[3] == "error":
                    errors.append(f'{bcolors.FAIL}{match[3]} File: {match[0].split("/")[-1]} Line {match[1]} Column {match[2]} - {match[5]}{bcolors.ENDC}\n')
                elif warning_required:
                    errors.append(f'{bcolors.WARNING}{match[3]}: {match[0].split("/")[-1]} Line {match[1]} Column {match[2]} - {match[5]}{bcolors.ENDC}\n')
            else:
                if match[3] == "warning" and not warning_required:
                    continue
                errors.append(f'{match[3]}: {match[0].split("/")[-1]} Line {match[1]} Column {match[2]} - {match[5]}\n')
    except Exception:
        pass

    return errors

def _parse_python_errors(python_output: str, color_coding_required: bool) -> list:
    from re import findall
    errors = []

    try:
        for match in findall(r'\*\*\*   File "/LeanCLI/([^"]+)", line (\d+)\n.*\n(.*)\^.*\n(.*)', python_output):
            if color_coding_required:
                errors.append(f"{bcolors.FAIL}Build Error File: {match[0]} Line {match[1]} Column {match[2]} - {match[3]}{bcolors.ENDC}\n")
            else:
                errors.append(f"Build Error File: {match[0]} Line {match[1]} Column {match[2]} - {match[3]}\n")

        for match in re.findall(r"\*\*\* Sorry: ([^(]+) \(([^,]+), line (\d+)\)", python_output):
            if color_coding_required:
                errors.append(f"{bcolors.FAIL}Build Error File: {match[1]} Line {match[2]} Column 0 - {match[0]}{bcolors.ENDC}\n")
            else:
                errors.append(f"Build Error File: {match[1]} Line {match[2]} Column 0 - {match[0]}\n")
    except Exception:
        pass

    return errors


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[33m'
    FAIL = '\033[31m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
