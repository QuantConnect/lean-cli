import json
from typing import Dict, Any
from lean.container import container
import sys
import io
from contextlib import redirect_stdout
import re

docker_manager = container.docker_manager()
project_manager = container.project_manager()
lean_runner = container.lean_runner()
temp_manager = container.temp_manager()
project_config_manager = container.project_config_manager()
cli_config_manager = container.cli_config_manager()
logger = container.logger()

def _compile() -> Dict[str, Any]:
    """
    This function compile c# and python project files.
    """
    message = {
        "result": False,
        "algorithmType": "",
    }

    project_id = int(sys.argv[-1])
    project_dir = project_manager.get_project_by_id(project_id)
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

    lean_runner.setup_language_specific_run_options(run_options, project_dir, algorithm_file, False, False)

    project_config = project_config_manager.get_project_config(project_dir)
    engine_image = cli_config_manager.get_engine_image(
        project_config.get("engine-image", None))

    message["result"] = docker_manager.run_image(engine_image, **run_options)
    temp_manager.delete_temporary_directories_when_done = False
    return message

def create_success() -> Dict[str, Any]:
    return json.dumps({
        "eType": "BuildSuccess",
    })

def parse_csharp_errors(csharp_output) -> list:
    errors = []

    relevant_output = csharp_output[csharp_output.index("Build FAILED."):]
    for match in re.findall(r"(.*)\((\d+),(\d+)\): (error|warning) ([a-zA-Z0-9]+): ([^[]+) ", relevant_output):
        errors.append(f'{match[3]} File: {match[0].split("/")[-1]} Line {match[1]} Column {match[2]} - {match[5]} \n')

    return errors

def parse_python_errors(python_output) -> list:
    errors = []

    for match in re.findall(r'\*\*\*   File "/LeanCLI/([^"]+)", line (\d+)\n.*\n(.*)\^.*\n(.*)', python_output):
        errors.append(f"Build Error File: {match[0]} Line {match[1]} Column {match[2]} - {match[3]} \n")

    for match in re.findall(r"\*\*\* Sorry: ([^(]+) \(([^,]+), line (\d+)\)", python_output):
        errors.append(f"Build Error File: {match[1]} Line {match[2]} Column 0 - {match[0]} \n")

    return errors

def create_error(algorithm_type, message) -> Dict[str, Any]:

    errors = []
    if algorithm_type == "csharp":
        errors.extend(parse_csharp_errors(message))
    elif algorithm_type == "python":
        errors.extend(parse_python_errors(message))

    return json.dumps({
        "eType": "BuildError",
        "aErrors": errors,
    })

def redirect_stdout_of_subprocess(method_name_to_run, *args, **kwargs) -> tuple:
    """ It captures the stdout of the method given to run.

    :param method_name_to_run: name of the method to run
    :return: result of the method and the stdout of the process
    """
    f = io.StringIO()
    with redirect_stdout(f):
        result = method_name_to_run(*args, **kwargs)
    stdout = f.getvalue()
    return (result, stdout)

def compile() -> None:
    """This is a utility function that is used by the vscode plugin project.
    """
    compile_result, stdout = redirect_stdout_of_subprocess(_compile)
    if compile_result["result"]:
        processed_output = create_success()
    else:
        processed_output = create_error(compile_result["algorithmType"], stdout)
    logger.info(processed_output)