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

import asyncio
import json
from pathlib import Path
from unittest import mock

from click.testing import CliRunner
from textual.widgets import TabbedContent

from lean.commands import lean
from lean.container import container
from lean.ui import app as ui_app
from lean.ui.actions import ACTIONS, format_command
from lean.ui.app import ConfirmScreen, LeanApp, ProjectTable
from lean.ui.backtest_screen import BacktestScreen
from lean.ui.projects import UIProject, discover_local_projects, filter_projects, merge_cloud_projects
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory
from tests.test_ui_results import create_local_backtest, create_result


def _discover() -> list:
    return discover_local_projects(Path.cwd(), [Path.cwd() / "data"])


def _action(key: str):
    return next(a for a in ACTIONS if a.key == key)


def test_discover_local_projects_finds_projects_and_libraries() -> None:
    create_fake_lean_cli_directory()

    names = [p.name for p in _discover()]

    assert names == ["CSharp Project", "Library/CSharp Library", "Library/Python Library", "Python Project"]


def test_discover_local_projects_skips_project_output_and_data_directories() -> None:
    create_fake_lean_cli_directory()
    for path in [Path.cwd() / "Python Project" / "backtests" / "2026-01-01_00-00-00" / "config.json",
                 Path.cwd() / "data" / "some-dataset" / "config.json",
                 Path.cwd() / ".hidden" / "config.json"]:
        path.parent.mkdir(parents=True)
        path.write_text("{}")

    names = [p.name for p in _discover()]

    assert names == ["CSharp Project", "Library/CSharp Library", "Library/Python Library", "Python Project"]


def test_discover_local_projects_reads_project_config() -> None:
    create_fake_lean_cli_directory()
    config_path = Path.cwd() / "Python Project" / "config.json"
    config_path.write_text(json.dumps({"algorithm-language": "Python", "cloud-id": 7, "description": "Momentum"}))

    project = next(p for p in _discover() if p.name == "Python Project")

    assert project.language == "Py"
    assert project.cloud_id == 7
    assert project.description == "Momentum"
    assert project.path == Path.cwd() / "Python Project"


def test_merge_cloud_projects_matches_by_cloud_id_and_adds_cloud_only_projects() -> None:
    local = [UIProject("Synced", Path("Synced"), cloud_id=1),
             UIProject("Local Only", Path("Local Only")),
             UIProject("Deleted In Cloud", Path("Deleted In Cloud"), cloud_id=3)]
    cloud = [create_api_project(1, "Synced Cloud Name"), create_api_project(2, "Cloud Only")]

    merged = {p.name: p for p in merge_cloud_projects(local, cloud)}

    assert list(merged) == ["Cloud Only", "Deleted In Cloud", "Local Only", "Synced"]
    assert merged["Synced"].location == "synced"
    assert merged["Local Only"].location == "local"
    assert merged["Deleted In Cloud"].location == "local"
    assert merged["Cloud Only"].location == "cloud"
    assert merged["Cloud Only"].cloud_id == 2


def test_filter_projects_matches_every_word_ignoring_case() -> None:
    projects = [UIProject("Momentum Strategy"), UIProject("Mean Reversion"), UIProject("Library/Momentum Utils")]

    assert [p.name for p in filter_projects(projects, "momentum strat")] == ["Momentum Strategy"]
    assert [p.name for p in filter_projects(projects, "MOMENTUM")] == ["Momentum Strategy", "Library/Momentum Utils"]
    assert len(filter_projects(projects, "")) == 3


def test_actions_are_unavailable_when_project_or_login_is_missing() -> None:
    local = UIProject("Local", Path("Local"))
    cloud = UIProject("Cloud", cloud_id=5)

    assert _action("b").unavailable_reason(local, logged_in=False) is None
    assert _action("b").unavailable_reason(cloud, logged_in=True) == "pull it first"
    assert _action("p").unavailable_reason(local, logged_in=False) == "run `lean login` first"
    assert _action("u").unavailable_reason(local, logged_in=True) == "push it first"
    assert _action("u").unavailable_reason(cloud, logged_in=True) is None


def test_action_commands() -> None:
    local = UIProject("My Project", Path("My Project"))
    cloud = UIProject("Cloud Project", cloud_id=5)

    assert format_command(_action("b").build_args(local)) == "lean backtest 'My Project'"
    assert _action("c").build_args(local) == ["cloud", "backtest", "My Project", "--push"]
    assert _action("c").build_args(cloud) == ["cloud", "backtest", "5"]
    assert _action("u").build_args(cloud) == ["cloud", "pull", "--project", "5"]


def test_ui_requires_lean_config() -> None:
    result = CliRunner().invoke(lean, ["ui"])

    assert result.exit_code != 0
    assert "requires a Lean configuration file" in str(result.exception)


def _run_app(test) -> None:
    """Runs a test coroutine against the app with the fake Lean CLI directory and no stored credentials."""
    create_fake_lean_cli_directory()
    container.cli_config_manager.user_id.get_value = mock.Mock(return_value=None)

    async def run() -> None:
        app = LeanApp(Path.cwd(), Path.cwd() / "data")
        async with app.run_test(size=(140, 40)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            await test(app, pilot)

    asyncio.run(run())


def test_app_lists_local_projects_and_filters_them() -> None:
    async def test(app: LeanApp, pilot) -> None:
        table = app.query_one(ProjectTable)
        assert table.row_count == 4

        await pilot.press("slash", *"python")
        assert table.row_count == 2
        assert [p.name for p in app._visible] == ["Library/Python Library", "Python Project"]

        await pilot.press("escape")
        assert table.row_count == 4
        assert table.has_focus

    _run_app(test)


def test_app_moves_through_projects_with_the_keyboard() -> None:
    async def test(app: LeanApp, pilot) -> None:
        assert app.selected_project.name == "CSharp Project"

        await pilot.press("j", "j", "j")
        assert app.selected_project.name == "Python Project"

        await pilot.press("k")
        assert app.selected_project.name == "Library/Python Library"

    _run_app(test)


def test_app_asks_for_confirmation_before_running_a_command() -> None:
    async def test(app: LeanApp, pilot) -> None:
        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            await pilot.press("b")
            assert isinstance(app.screen, ConfirmScreen)
            assert app.screen._command == "lean backtest 'CSharp Project'"

            await pilot.press("n")
            assert not isinstance(app.screen, ConfirmScreen)
            command_process.assert_not_called()

    _run_app(test)


def test_app_runs_the_selected_action_and_shows_its_output() -> None:
    async def test(app: LeanApp, pilot) -> None:
        def fake_run(on_line):
            on_line("Backtest finished")
            return 0

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run

            await pilot.press("enter")
            assert app.focused.__class__.__name__ == "ActionList"
            await pilot.press("enter", "y")
            await app.workers.wait_for_complete()
            await pilot.pause()

        command_process.assert_called_once_with(["backtest", "CSharp Project"], Path.cwd())
        output = app.query_one("#output")
        lines = [line.text for line in output.lines]
        assert "Backtest finished" in lines
        assert output.border_subtitle == "done"

    _run_app(test)


def test_app_does_not_run_unavailable_actions() -> None:
    async def test(app: LeanApp, pilot) -> None:
        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            await pilot.press("p")
            assert not isinstance(app.screen, ConfirmScreen)
            command_process.assert_not_called()

    _run_app(test)


def test_command_process_runs_the_cli_as_a_child_process(fake_filesystem) -> None:
    from lean import __version__
    from lean.ui.actions import CommandProcess

    lines = []
    fake_filesystem.pause()
    try:
        exit_code = CommandProcess(["--version"], Path(__file__).parent).run(lines.append)
    finally:
        fake_filesystem.resume()

    assert exit_code == 0
    assert lines == [f"lean {__version__}"]


def test_view_results_is_unavailable_without_local_backtests() -> None:
    async def test(app: LeanApp, pilot) -> None:
        await pilot.press("v")
        assert not isinstance(app.screen, BacktestScreen)
        assert _action("v").unavailable_reason(app.selected_project, logged_in=False) == "no local backtests yet"

    _run_app(test)


def test_app_opens_backtest_results_with_charts_statistics_and_orders() -> None:
    async def test(app: LeanApp, pilot) -> None:
        create_local_backtest(Path.cwd() / "CSharp Project", "2026-10-08_16-00-57", create_result())

        await pilot.press("v")
        await app.workers.wait_for_complete()
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, BacktestScreen)
        assert screen.query_one("#summary").border_title == "2026-10-08_16-00-57: Completed"
        assert screen.query_one("#equity")._lines[0].label == "Equity"
        assert screen.query_one("#equity")._lines[1].label == "Benchmark"
        assert screen.query_one("#orders-table").row_count == 2

        await pilot.press("3")
        assert screen.query_one(TabbedContent).active == "charts"
        assert screen.query_one("#chart-names").option_count == 4

        await pilot.press("escape")
        assert not isinstance(app.screen, BacktestScreen)

    _run_app(test)


def test_backtest_screen_switches_between_backtests() -> None:
    async def test(app: LeanApp, pilot) -> None:
        project_dir = Path.cwd() / "CSharp Project"
        create_local_backtest(project_dir, "2026-10-08_16-00-57", create_result())
        create_local_backtest(project_dir, "2026-10-09_09-30-00", create_result(status="Running"))

        await pilot.press("v")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.screen.query_one("#summary").border_title.startswith("2026-10-09_09-30-00: Running")

        await pilot.press("j")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.screen.query_one("#summary").border_title == "2026-10-08_16-00-57: Completed"

    _run_app(test)


def test_backtest_screen_shows_a_message_for_backtests_without_results() -> None:
    async def test(app: LeanApp, pilot) -> None:
        (Path.cwd() / "CSharp Project" / "backtests" / "2026-10-08_16-00-57").mkdir(parents=True)

        await pilot.press("v")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert "No results found" in str(app.screen.query_one("#summary").render())

    _run_app(test)


def test_project_keys_do_not_run_actions_on_other_screens() -> None:
    async def test(app: LeanApp, pilot) -> None:
        create_local_backtest(Path.cwd() / "CSharp Project", "2026-10-08_16-00-57", create_result())
        await pilot.press("v")
        await pilot.pause()

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            await pilot.press("b")
            assert isinstance(app.screen, BacktestScreen)
            command_process.assert_not_called()

    _run_app(test)


def test_projects_can_update_while_another_screen_is_shown() -> None:
    async def test(app: LeanApp, pilot) -> None:
        await pilot.press("b")
        assert isinstance(app.screen, ConfirmScreen)

        app._set_projects(app._projects[:1], logged_in=False, status="updated")
        await pilot.pause()

        assert app.screen_stack[0].query_one(ProjectTable).row_count == 1

    _run_app(test)
