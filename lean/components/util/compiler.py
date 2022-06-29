import hashlib
import uuid
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

def _compile() -> bool:
    message = {
        "result": False,
        "algorithmType": "",
    }

    project_id = int(sys.argv[-1])
    project_dir = project_manager.get_project_by_id(project_id)

    compile_id = uuid.uuid4().hex

    # The dict containing all options passed to `docker run`
    # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
    run_options: Dict[str, Any] = {
        "name": f"lean_cli_compile_{project_id}_{compile_id}",
        "commands": [],
        "environment": {},
        "mounts": [],
        "volumes": {}
    }

    algorithm_file = project_manager.find_algorithm_file(project_dir)

    if algorithm_file.name.endswith(".py"):
        lean_runner.set_up_python_options(project_dir, run_options)
        message["algorithmType"] = "python"
    else:
        lean_runner.set_up_common_csharp_options(run_options)
        lean_runner.set_up_csharp_options(project_dir, run_options, True)
        message["algorithmType"] = "csharp"

    project_config = project_config_manager.get_project_config(project_dir)
    engine_image = cli_config_manager.get_engine_image(
        project_config.get("engine-image", None))

    try:
        message["result"] = docker_manager.run_image(engine_image, **run_options)
    except Exception as e:
        pass
    temp_manager.delete_temporary_directories_when_done = False
    return message

def broadcast_success():
    return {
        "eType": "BuildSuccess",
    }

def parse_csharp_errors(csharp_output):
    errors = []

    relevant_output = csharp_output[csharp_output.index("Build FAILED."):]
    for match in re.findall(r"(.*)\((\d+),(\d+)\): (error|warning) ([a-zA-Z0-9]+): ([^[]+) ", relevant_output):
        errors.append({
            "iLine": int(match[1]),
            "iColumn": int(match[2]),
            "sType": match[3],
            "sErrorText": match[5],
            "sErrorFilename": match[0].split("/")[-1]
        })

    return errors

def parse_python_errors(python_output):
    errors = []

    for match in re.findall(r'\*\*\*   File "/LeanCLI/([^"]+)", line (\d+)\n.*\n(.*)\^.*\n(.*)', python_output):
        errors.append({
            "iLine": int(match[1]),
            "iColumn": len(match[2]),
            "sType": "error",
            "sErrorText": match[3],
            "sErrorFilename": match[0]
        })

    for match in re.findall(r"\*\*\* Sorry: ([^(]+) \(([^,]+), line (\d+)\)", python_output):
        errors.append({
            "iLine": int(match[2]),
            "iColumn": 0,
            "sType": "error",
            "sErrorText": match[0],
            "sErrorFilename": match[1]
        })

    return errors

def broadcast_error(algorithm_type, output):

    errors = []
    if algorithm_type is "csharp":
        errors.extend(parse_csharp_errors(output))
    elif algorithm_type is "python":
        errors.extend(parse_python_errors(output))

    return {
        "eType": "BuildError",
        "aErrors": errors,
    }


def compile_create():
    f = io.StringIO()
    with redirect_stdout(f):
        compile_data = _compile()
    stdout = f.getvalue()
    if compile_data["result"]:
        processed_output = broadcast_success()
    else:
        processed_output = broadcast_error(compile_data["algorithmType"], stdout)
    logger.info(processed_output) 