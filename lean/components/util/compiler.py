import hashlib
import uuid
from typing import Dict, Any
from xmlrpc.client import boolean
from lean.container import container

docker_manager = container.docker_manager()
project_manager = container.project_manager()
lean_runner = container.lean_runner()
temp_manager = container.temp_manager()
project_config_manager = container.project_config_manager()
cli_config_manager = container.cli_config_manager()
logger = container.logger()


def compile_create(project_id: int) -> boolean:
    project_dir = project_manager.get_project_by_id(project_id)

    compile_id = uuid.uuid4().hex

    source_files = project_manager.get_source_files(project_dir)

    signature_content = ""
    for file in sorted(source_files):
        if not file.name.endswith(".ipynb"):
            signature_content += file.read_text(encoding="utf-8")
    signature = hashlib.md5(signature_content.encode("utf-8")).hexdigest()

    # The dict containing all options passed to `docker run`
    # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
    run_options: Dict[str, Any] = {
        "detach": True,
        "name": f"lean_cli_compile_{project_id}_{compile_id}",
        "commands": [],
        "environment": {},
        "mounts": [],
        "volumes": {}
    }

    algorithm_file = project_manager.find_algorithm_file(project_dir)
    if algorithm_file.name.endswith(".py"):
        lean_runner.set_up_python_options(project_dir, run_options)

        source_files = [file.relative_to(
            project_dir).as_posix() for file in source_files]
        source_files = [f'"/LeanCLI/{file}"' for file in source_files]

        run_options["commands"].append(
            f"python -m compileall {' '.join(source_files)} > /output-python.txt")
    else:
        lean_runner.set_up_common_csharp_options(run_options)
        lean_runner.set_up_csharp_options(project_dir, run_options, False)

        dotnet_build_index = next(i for i, v in enumerate(
            run_options["commands"]) if v.startswith("dotnet build"))
        run_options["commands"][dotnet_build_index] += " > /output-csharp.txt"

    project_config = project_config_manager.get_project_config(project_dir)
    engine_image = cli_config_manager.get_engine_image(
        project_config.get("engine-image", None))

    try:
        docker_manager.run_image(engine_image, **run_options)
        result = True
    except Exception as e:
        logger.error(f"Something went wrong while compiling: {e}")
        result = False

    temp_manager.delete_temporary_directories_when_done = False
    return result
