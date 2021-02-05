from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from lean.commands import lean
from lean.constants import DEFAULT_LEAN_CONFIG_FILE, LEAN_ENGINE_DOCKER_IMAGE, LEAN_ENGINE_DOCKER_TAG
from tests.test_helpers import create_fake_lean_cli_project


def setup_mocks(from_env, system, status_code: int) -> mock.Mock:
    """Mock docker.from_env() and os.system()."""
    docker_client = mock.Mock()
    container = mock.Mock()

    docker_client.ping.return_value = True
    docker_client.images.list.return_value = []
    docker_client.containers.run.return_value = container

    container.logs.return_value = iter(())
    container.wait.return_value = {"StatusCode": status_code}

    from_env.return_value = docker_client
    system.return_value = status_code

    return docker_client


@mock.patch("os.system")
@mock.patch("docker.from_env")
def test_backtest_should_abort_when_lean_config_not_available(from_env, system) -> None:
    create_fake_lean_cli_project()
    (Path.cwd() / DEFAULT_LEAN_CONFIG_FILE).unlink()

    setup_mocks(from_env, system, 0)

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code != 0


@mock.patch("os.system")
@mock.patch("docker.from_env")
def test_backtest_should_abort_when_project_does_not_exist(from_env, system) -> None:
    create_fake_lean_cli_project()

    setup_mocks(from_env, system, 0)

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0


@mock.patch("os.system")
@mock.patch("docker.from_env")
def test_backtest_should_abort_when_project_does_not_contain_algorithm_file(from_env, system) -> None:
    create_fake_lean_cli_project()
    (Path.cwd() / "Empty Project").mkdir()

    setup_mocks(from_env, system, 0)

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Empty Project"])

    assert result.exit_code != 0


@mock.patch("os.system")
@mock.patch("docker.from_env")
def test_backtest_should_create_directory_for_output(from_env, system) -> None:
    create_fake_lean_cli_project()

    setup_mocks(from_env, system, 0)

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    backtests_dir = (Path.cwd() / "Python Project" / "backtests")
    assert backtests_dir.exists()
    assert next(backtests_dir.iterdir(), None) is not None


@mock.patch("os.system")
@mock.patch("docker.from_env")
def test_backtest_should_add_volume_containing_source_code_when_python_project_given(from_env, system) -> None:
    create_fake_lean_cli_project()

    docker_client = setup_mocks(from_env, system, 0)

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    _, last_run_args, last_run_kwargs = [x for x in docker_client.containers.mock_calls if x[0] == "run"][-1]

    assert next((x for x in last_run_kwargs["volumes"].values() if x["bind"] == "/Project"), None) is not None


@mock.patch("os.system")
@mock.patch("docker.from_env")
def test_backtest_should_mount_compiled_dll_when_csharp_project_given(from_env, system) -> None:
    create_fake_lean_cli_project()

    docker_client = setup_mocks(from_env, system, 0)

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "CSharp Project"])

    assert result.exit_code == 0

    _, last_run_args, last_run_kwargs = [x for x in docker_client.containers.mock_calls if x[0] == "run"][-1]

    target_dll = "QuantConnect.Algorithm.CSharp.dll"
    assert next((x for x in last_run_kwargs["mounts"] if target_dll in x["Target"]), None) is not None


@mock.patch("os.system")
@mock.patch("docker.from_env")
def test_backtest_should_run_default_image_and_tag_when_no_options_given(from_env, system) -> None:
    create_fake_lean_cli_project()

    docker_client = setup_mocks(from_env, system, 0)

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    _, last_run_args, last_run_kwargs = [x for x in docker_client.containers.mock_calls if x[0] == "run"][-1]
    assert last_run_args[0] == f"{LEAN_ENGINE_DOCKER_IMAGE}:{LEAN_ENGINE_DOCKER_TAG}"


@mock.patch("os.system")
@mock.patch("docker.from_env")
def test_backtest_should_fail_when_running_docker_image_fails(from_env, system) -> None:
    create_fake_lean_cli_project()

    setup_mocks(from_env, system, 1)

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 1
