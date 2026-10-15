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
import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from textual.widgets import TabbedContent

from lean.container import container
from lean.ui import app as ui_app
from lean.ui import backtest_screen
from lean.ui.actions import ACTIONS, CommandProcess, format_command, parse_cloud_backtest_url
from lean.ui.app import ConfirmScreen, LeanApp, ProjectTable
from lean.ui.backtest_screen import BacktestPicker, BacktestScreen, LiveRun
from lean.ui.projects import UIProject, discover_local_projects, filter_projects, merge_cloud_projects
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory
from lean.ui.results import CloudBacktest, LocalBacktest, PendingCloudBacktest
from tests.ui.test_results import (BACKTEST_ID, create_cloud_backtest, create_cloud_orders, create_local_backtest,
                                   create_result, mock_cloud_api)


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
    assert _action("c").unavailable_reason(local, logged_in=False) == "run `lean login` first"
    assert _action("c").unavailable_reason(cloud, logged_in=True) is None
    assert _action("p").unavailable_reason(local, logged_in=False) == "run `lean login` first"
    assert _action("u").unavailable_reason(local, logged_in=True) == "push it first"
    assert _action("u").unavailable_reason(cloud, logged_in=True) is None


def test_view_results_needs_local_backtests_or_a_cloud_project() -> None:
    local = UIProject("Local", Path.cwd() / "Local")
    cloud = UIProject("Cloud", cloud_id=5)

    assert _action("v").unavailable_reason(local, logged_in=True) == "no backtests yet"
    assert _action("v").unavailable_reason(cloud, logged_in=False) == "run `lean login` first"
    assert _action("v").unavailable_reason(cloud, logged_in=True) is None

    create_local_backtest(local.path, "2026-10-08_16-00-57", create_result())
    assert _action("v").unavailable_reason(local, logged_in=False) is None


def test_action_commands() -> None:
    local = UIProject("My Project", Path("My Project"))
    cloud = UIProject("Cloud Project", cloud_id=5)

    assert format_command(_action("b").build_args(local)) == "lean backtest 'My Project'"
    assert _action("c").build_args(local) == ["cloud", "backtest", "My Project", "--push"]
    assert _action("c").build_args(cloud) == ["cloud", "backtest", "5"]
    assert _action("u").build_args(cloud) == ["cloud", "pull", "--project", "5"]


def test_parse_cloud_backtest_url_reads_the_project_and_backtest_ids() -> None:
    url = f"Backtest url: https://www.quantconnect.com/project/19213997/{BACKTEST_ID}"

    assert parse_cloud_backtest_url(url) == (19213997, BACKTEST_ID)
    assert parse_cloud_backtest_url("Started compiling project 'CSharp Project'") is None


def test_command_process_runs_the_cli_as_a_child_process() -> None:
    from lean import __version__
    from lean.ui.actions import CommandProcess

    lines = []
    exit_code = CommandProcess(["--version"], Path(__file__).parent).run(lines.append)

    assert exit_code == 0
    assert lines == [f"lean {__version__}"]


def test_command_process_honors_a_stop_asked_before_it_started() -> None:
    process = CommandProcess(["--version"], Path.cwd())
    process.stop()

    with mock.patch("subprocess.Popen") as popen:
        popen.return_value.stdout = iter(["lean 0.0.0\n"])
        popen.return_value.poll.return_value = None
        popen.return_value.wait.return_value = 1
        exit_code = process.run(lambda line: None)

    popen.return_value.send_signal.assert_called_once()
    assert exit_code == 1


def test_command_process_interrupts_twice_then_kills() -> None:
    process = CommandProcess(["--version"], Path.cwd())

    with mock.patch("subprocess.Popen") as popen:
        popen.return_value.stdout = iter([])
        popen.return_value.poll.return_value = None
        popen.return_value.wait.return_value = 0
        process.run(lambda line: None)
        for _ in range(3):
            process.stop()

    assert popen.return_value.send_signal.call_count == 2
    popen.return_value.kill.assert_called_once()


def test_command_process_wait_kills_a_command_that_does_not_stop() -> None:
    from subprocess import TimeoutExpired
    process = CommandProcess(["--version"], Path.cwd())

    with mock.patch("subprocess.Popen") as popen:
        popen.return_value.stdout = iter([])
        popen.return_value.wait.side_effect = [0, TimeoutExpired("lean", 1)]
        process.run(lambda line: None)
        process.wait(1)

    popen.return_value.kill.assert_called_once()


def _run_app(test, logged_in: bool = False) -> None:
    """Runs a test coroutine against the app with the fake Lean CLI directory and no cloud projects."""
    create_fake_lean_cli_directory()

    async def run() -> None:
        with mock.patch.object(ui_app, "is_logged_in", return_value=logged_in), \
                mock.patch.object(ui_app, "fetch_cloud_projects", return_value=[]):
            app = LeanApp(Path.cwd(), Path.cwd() / "data")
            async with app.run_test(size=(140, 40)) as pilot:
                await _settle(app, pilot)
                await test(app, pilot)

    asyncio.run(run())


async def _settle(app: LeanApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


async def _settle_results(app: LeanApp, pilot) -> None:
    """Waits for the results screen to load, while the command it runs is still going."""
    for _ in range(3):
        # An empty list makes wait_for_complete wait for every worker, including the command's
        result_workers = [w for w in app.workers if w.group == "result"]
        if result_workers:
            await app.workers.wait_for_complete(result_workers)
        await pilot.pause()


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


def test_app_shows_it_is_loading_until_the_projects_arrive() -> None:
    create_fake_lean_cli_directory()
    release = threading.Event()

    def slow_discover(root, skip_dirs):
        release.wait(5)
        return discover_local_projects(root, skip_dirs)

    async def run() -> None:
        with mock.patch.object(ui_app, "is_logged_in", return_value=False),                 mock.patch.object(ui_app, "discover_local_projects", side_effect=slow_discover):
            app = LeanApp(Path.cwd(), Path.cwd() / "data")
            async with app.run_test(size=(140, 40)) as pilot:
                await pilot.pause()
                table = app.query_one(ProjectTable)
                assert table.loading
                assert table.border_subtitle == "loading projects..."

                release.set()
                await _settle(app, pilot)
                assert not table.loading
                assert table.has_focus
                assert table.row_count == 4

                await pilot.press("r")
                assert not table.loading

    asyncio.run(run())


def test_app_moves_through_projects_with_the_keyboard() -> None:
    async def test(app: LeanApp, pilot) -> None:
        assert app.selected_project.name == "CSharp Project"

        await pilot.press("j", "j", "j")
        assert app.selected_project.name == "Python Project"

        await pilot.press("k")
        assert app.selected_project.name == "Library/Python Library"

    _run_app(test)


def test_app_asks_for_confirmation_before_pushing() -> None:
    async def test(app: LeanApp, pilot) -> None:
        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            await pilot.press("p")
            assert isinstance(app.screen, ConfirmScreen)
            assert app.screen._command == "lean cloud push --project 'CSharp Project'"

            await pilot.press("n")
            assert not isinstance(app.screen, ConfirmScreen)
            command_process.assert_not_called()

    _run_app(test, logged_in=True)


def test_app_runs_a_confirmed_command_and_shows_its_output() -> None:
    async def test(app: LeanApp, pilot) -> None:
        def fake_run(on_line):
            on_line("Successfully pushed 'CSharp Project'")
            return 0

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run
            await pilot.press("p", "y")
            await _settle(app, pilot)

        command_process.assert_called_once_with(["cloud", "push", "--project", "CSharp Project"], Path.cwd())
        output = app.query_one("#output")
        assert "Successfully pushed 'CSharp Project'" in [line.text for line in output.lines]
        assert output.border_subtitle == "done"

    _run_app(test, logged_in=True)


def test_app_does_not_run_unavailable_actions() -> None:
    async def test(app: LeanApp, pilot) -> None:
        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            await pilot.press("p")
            assert not isinstance(app.screen, ConfirmScreen)
            command_process.assert_not_called()

    _run_app(test)


def test_quitting_waits_for_the_running_command_to_stop() -> None:
    async def test(app: LeanApp, pilot) -> None:
        finish = threading.Event()

        def fake_run(on_line):
            finish.wait(5)
            return 0

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run
            command_process.return_value.stop_requested = False
            command_process.return_value.wait.side_effect = lambda timeout: finish.set()
            await pilot.press("p", "y", "q")
            await _settle(app, pilot)

        command_process.return_value.stop.assert_called_once_with()
        command_process.return_value.wait.assert_called_once_with(ui_app.QUIT_TIMEOUT_SECONDS)
        assert not app.is_running

    _run_app(test, logged_in=True)


def test_quitting_does_not_force_a_command_that_is_already_stopping() -> None:
    async def test(app: LeanApp, pilot) -> None:
        finish = threading.Event()

        def fake_run(on_line):
            finish.wait(5)
            return 0

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run
            command_process.return_value.stop_requested = True
            command_process.return_value.wait.side_effect = lambda timeout: finish.set()
            await pilot.press("p", "y", "q")
            await _settle(app, pilot)

        command_process.return_value.stop.assert_not_called()
        command_process.return_value.wait.assert_called_once_with(ui_app.QUIT_TIMEOUT_SECONDS)

    _run_app(test, logged_in=True)


def _stop_cloud_backtest(answer: str):
    """Runs a cloud backtest, presses x once it has its id and answers the question, returning the API mock."""
    async def test(app: LeanApp, pilot) -> None:
        mock_cloud_api(create_cloud_backtest(completed=False, progress=0.5))
        delete = container.api_client.backtests.delete = mock.Mock()
        finish = threading.Event()

        def fake_run(on_line):
            on_line(f"Backtest url: https://www.quantconnect.com/project/123/{BACKTEST_ID}")
            finish.wait(5)
            return 1

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run
            command_process.return_value.stop_requested = False
            command_process.return_value.stop.side_effect = finish.set
            await pilot.press("c")
            await _settle_results(app, pilot)
            await pilot.press("x")
            assert isinstance(app.screen, ConfirmScreen)
            await pilot.press(answer)
            await _settle(app, pilot)

        command_process.return_value.stop.assert_called_once_with()
        test.delete_calls = delete.call_args_list

    _run_app(test, logged_in=True)
    return test.delete_calls


def test_stopping_a_cloud_backtest_can_delete_it() -> None:
    assert _stop_cloud_backtest("y") == [mock.call(123, BACKTEST_ID)]


def test_stopping_a_cloud_backtest_can_keep_it_running() -> None:
    assert _stop_cloud_backtest("n") == []


def test_app_runs_one_command_at_a_time() -> None:
    async def test(app: LeanApp, pilot) -> None:
        finish = threading.Event()

        def fake_run(on_line):
            finish.wait(5)
            return 0

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run
            await pilot.press("p", "y", "b")
            assert app._process is not None
            finish.set()
            await _settle(app, pilot)

        command_process.assert_called_once_with(["cloud", "push", "--project", "CSharp Project"], Path.cwd())
        assert app._process is None

    _run_app(test, logged_in=True)


def test_backtesting_locally_opens_the_results_while_the_backtest_runs() -> None:
    async def test(app: LeanApp, pilot) -> None:
        screen_loaded = threading.Event()

        def fake_run(on_line):
            output_dir = Path(command_process.call_args.args[0][3])
            on_line("Starting LEAN")
            # LEAN writes the result file after the results screen has opened without one
            screen_loaded.wait(5)
            create_local_backtest(output_dir.parent.parent, output_dir.name, create_result())
            return 0

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run
            await pilot.press("b")
            assert isinstance(app.screen, BacktestScreen)
            await _settle_results(app, pilot)
            screen_loaded.set()
            await _settle(app, pilot)

        args = command_process.call_args.args[0]
        assert args[:3] == ["backtest", "CSharp Project", "--output"]
        assert Path(args[3]).parent == Path.cwd() / "CSharp Project" / "backtests"

        screen = app.screen
        assert screen.query_one("#summary").border_title.endswith("(local): Completed")
        assert len(screen.query_one("#equity").points) == 5
        assert screen.query_one(TabbedContent).active == "logs"
        assert "Starting LEAN" in [line.text for line in screen.query_one("#log").lines]

    _run_app(test)


def test_backtesting_in_the_cloud_switches_to_the_backtest_once_it_is_created() -> None:
    async def test(app: LeanApp, pilot) -> None:
        mock_cloud_api(create_cloud_backtest())

        def fake_run(on_line):
            on_line("Started compiling project 'CSharp Project'")
            on_line(f"Backtest url: https://www.quantconnect.com/project/123/{BACKTEST_ID}")
            return 0

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run
            await pilot.press("c")
            assert isinstance(app.screen, BacktestScreen)
            await _settle(app, pilot)

        command_process.assert_called_once_with(["cloud", "backtest", "CSharp Project", "--push"], Path.cwd())
        screen = app.screen
        assert isinstance(screen.live_source, CloudBacktest)
        assert (screen.live_source.project_id, screen.live_source.backtest_id) == (123, BACKTEST_ID)
        assert screen.query_one("#summary").border_title == "Logical Red Monkey (cloud): Completed"
        assert len(screen.query_one("#equity").points) == 5

    _run_app(test, logged_in=True)


def _new_screen(*args) -> BacktestScreen:
    """Builds a screen outside the app, Python 3.9 needs an event loop for the lock every widget creates."""
    async def build() -> BacktestScreen:
        return BacktestScreen(*args)
    return asyncio.run(build())


def test_a_new_cloud_backtest_id_keeps_showing_its_live_log() -> None:
    pending = PendingCloudBacktest()
    screen = _new_screen(UIProject("CSharp Project"), True, LiveRun(pending, lines=["Started compiling"]))

    screen.set_live_source(CloudBacktest(123, BACKTEST_ID))

    assert screen.backtest.id == BACKTEST_ID
    assert screen._log_loaded_for == BACKTEST_ID


def test_a_new_cloud_backtest_id_keeps_the_backtest_the_user_moved_to() -> None:
    project = UIProject("CSharp Project", path=Path.cwd() / "CSharp Project")
    pending = PendingCloudBacktest()
    listed = CloudBacktest(123, BACKTEST_ID)
    older = LocalBacktest(Path.cwd() / "CSharp Project" / "backtests" / "2026-10-01_10-00-00")
    screen = _new_screen(project, True, LiveRun(pending, lines=[]))
    # The listing already holds the new backtest, so replacing the pending one shifts the older one down
    screen._backtests = [pending, listed, older]
    screen._selected = 2

    screen.set_live_source(CloudBacktest(123, BACKTEST_ID))

    assert screen.backtest is older
    assert [b.id for b in screen._backtests] == [BACKTEST_ID, older.id]


def test_a_failed_cloud_backtest_shows_the_failure() -> None:
    async def test(app: LeanApp, pilot) -> None:
        def fake_run(on_line):
            on_line("Build Error: main.py line 3")
            return 1

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            command_process.return_value.run.side_effect = fake_run
            await pilot.press("c")
            await _settle(app, pilot)

        screen = app.screen
        assert screen.query_one("#summary").border_title == \
            "New cloud backtest (cloud): failed (exit code 1), see Logs"
        assert "Build Error: main.py line 3" in [line.text for line in screen.query_one("#log").lines]

    _run_app(test, logged_in=True)


def test_results_screen_keys_do_not_reach_the_projects_screen() -> None:
    async def test(app: LeanApp, pilot) -> None:
        project_dir = Path.cwd() / "CSharp Project"
        create_local_backtest(project_dir, "2026-10-08_16-00-57", create_result())

        await pilot.press("v")
        await _settle(app, pilot)
        screen = app.screen
        assert isinstance(screen, BacktestScreen)

        with mock.patch.object(app, "_show_project") as show_project:
            await pilot.press("2")
            await _settle(app, pilot)
            await pilot.press("down", "enter")
            await _settle(app, pilot)

        show_project.assert_not_called()
        assert app.screen is screen

    _run_app(test)


def test_viewing_results_shows_the_newest_backtest() -> None:
    async def test(app: LeanApp, pilot) -> None:
        project_dir = Path.cwd() / "CSharp Project"
        create_local_backtest(project_dir, "2026-10-08_16-00-57", create_result())
        create_local_backtest(project_dir, "2026-10-09_09-30-00", create_result())

        await pilot.press("v")
        await _settle(app, pilot)

        screen = app.screen
        assert isinstance(screen, BacktestScreen)
        assert screen.query_one("#summary").border_title == "2026-10-09_09-30-00 (local): Completed"

        await pilot.press("2")
        await _settle(app, pilot)
        assert screen.query_one("#orders-table").row_count == 2

        await pilot.press("right_square_bracket")
        await _settle(app, pilot)
        assert screen.query_one("#summary").border_title == "2026-10-08_16-00-57 (local): Completed"

        await pilot.press("escape")
        assert not isinstance(app.screen, BacktestScreen)

    _run_app(test)


def test_results_list_local_and_cloud_backtests_newest_first() -> None:
    async def test(app: LeanApp, pilot) -> None:
        project = UIProject("Cloud Project", Path.cwd() / "Cloud Project", cloud_id=123)
        create_local_backtest(project.path, "2026-05-01_12-00-00", create_result())
        mock_cloud_api(create_cloud_backtest())

        app.push_screen(BacktestScreen(project, logged_in=True))
        await _settle(app, pilot)

        screen = app.screen
        assert [(b.location, b.name) for b in screen._backtests] == \
            [("cloud", "Logical Red Monkey"), ("local", "2026-05-01_12-00-00"), ("cloud", "Older")]
        assert screen.query_one("#summary").border_title == "Logical Red Monkey (cloud): Completed"

    _run_app(test, logged_in=True)


def test_backtest_picker_filters_and_opens_a_backtest() -> None:
    async def test(app: LeanApp, pilot) -> None:
        project_dir = Path.cwd() / "CSharp Project"
        create_local_backtest(project_dir, "2026-10-08_16-00-57", create_result())
        create_local_backtest(project_dir, "2026-10-09_09-30-00", create_result())

        await pilot.press("v")
        await _settle(app, pilot)
        await pilot.press("o")
        assert isinstance(app.screen, BacktestPicker)

        await pilot.press(*"10-08", "enter")
        await _settle(app, pilot)

        assert isinstance(app.screen, BacktestScreen)
        assert app.screen.query_one("#summary").border_title == "2026-10-08_16-00-57 (local): Completed"

    _run_app(test)


def test_results_of_a_running_backtest_refresh_until_it_finishes() -> None:
    async def test(app: LeanApp, pilot) -> None:
        running = create_result(status="Running", equity_points=5)
        equity = running["charts"]["Strategy Equity"]["series"]["Equity"]
        equity["values"] = equity["values"][:3]
        output_dir = create_local_backtest(Path.cwd() / "CSharp Project", "2026-10-08_16-00-57", running)

        await pilot.press("v")
        await _settle(app, pilot)
        screen = app.screen
        assert screen.query_one("#summary").border_title.startswith("2026-10-08_16-00-57 (local): Running ")
        assert screen._poll_timer is not None

        # The chart spans the whole backtest, so the partial equity only fills part of it
        chart = screen.query_one("#equity")
        period = (datetime(2013, 10, 7, tzinfo=timezone.utc).timestamp(),
                  datetime(2013, 10, 11, 23, 59, 59, tzinfo=timezone.utc).timestamp())
        assert chart.x_range == period
        assert chart.points[-1][0] < (period[0] + period[1]) / 2 + 3600

        (output_dir / "1121419604.json").write_text(json.dumps(create_result()))
        screen._poll()
        await _settle(app, pilot)

        assert screen.query_one("#summary").border_title == "2026-10-08_16-00-57 (local): Completed"
        assert screen._poll_timer is None

    _run_app(test)


def test_project_keys_do_not_run_actions_on_other_screens() -> None:
    async def test(app: LeanApp, pilot) -> None:
        create_local_backtest(Path.cwd() / "CSharp Project", "2026-10-08_16-00-57", create_result())
        await pilot.press("v")
        await _settle(app, pilot)

        with mock.patch.object(ui_app, "CommandProcess") as command_process:
            await pilot.press("b")
            assert isinstance(app.screen, BacktestScreen)
            command_process.assert_not_called()

    _run_app(test)


def test_projects_can_update_while_another_screen_is_shown() -> None:
    async def test(app: LeanApp, pilot) -> None:
        await pilot.press("p")
        assert isinstance(app.screen, ConfirmScreen)

        app._set_projects(app._projects[:1], logged_in=True, status="updated")
        await pilot.pause()

        assert app.screen_stack[0].query_one(ProjectTable).row_count == 1

    _run_app(test, logged_in=True)


async def _open_cloud_orders(app: LeanApp, pilot, backtest: dict, order_list: list) -> BacktestScreen:
    """Shows a cloud backtest's orders tab, with the API serving order_list."""
    project = UIProject("Cloud Project", cloud_id=123)
    post = mock_cloud_api(backtest, order_list=order_list)
    post.side_effect = _only_backtest(post.side_effect)
    app.push_screen(BacktestScreen(project, logged_in=True))
    await _settle(app, pilot)
    await pilot.press("2")
    await _settle(app, pilot)
    return app.screen


def _only_backtest(post):
    """Lists only the backtest under test, so the screen opens on it."""
    def answer(endpoint, payload):
        if endpoint == "backtests/list":
            return {"backtests": [{"backtestId": BACKTEST_ID, "name": "Logical Red Monkey",
                                   "created": "2026-10-08 19:45:10"}]}
        return post(endpoint, payload)
    return answer


class _OrdersAfter(list):
    """Orders that the fake orders endpoint only returns from its request number `after` + 1 on."""

    def __init__(self, after: int, orders: list) -> None:
        super().__init__(orders)
        self._after = after

    def __getitem__(self, index):
        if isinstance(index, slice):
            self._after -= 1
            if self._after >= 0:
                return []
        return super().__getitem__(index)

    def __len__(self) -> int:
        return super().__len__() if self._after < 0 else 0


def _order_requests() -> list:
    return [(c.args[1]["start"], c.args[1]["end"]) for c in container.api_client.post.call_args_list
            if c.args[0] == "backtests/orders/read"]


def _orders_label(screen: BacktestScreen) -> str:
    return str(screen.query_one(TabbedContent).get_tab("orders").label)


def test_orders_load_a_page_at_a_time_as_they_are_scrolled_to() -> None:
    async def test(app: LeanApp, pilot) -> None:
        screen = await _open_cloud_orders(app, pilot, create_cloud_backtest(), create_cloud_orders(250))
        table = screen.query_one("#orders-table")

        assert table.row_count == 100
        assert _orders_label(screen) == "Orders (100 of 250)"
        assert _order_requests() == [(0, 100)]

        table.move_cursor(row=95)
        await _settle(app, pilot)
        assert table.row_count == 200

        table.move_cursor(row=195)
        await _settle(app, pilot)
        assert table.row_count == 250
        assert _orders_label(screen) == "Orders (250)"
        assert _order_requests() == [(0, 100), (100, 200), (200, 300)]

        # Every order is shown, so reaching the end again asks for nothing
        table.move_cursor(row=249)
        await _settle(app, pilot)
        assert len(_order_requests()) == 3

    _run_app(test, logged_in=True)


def test_orders_of_a_running_backtest_add_new_orders_on_refresh() -> None:
    async def test(app: LeanApp, pilot) -> None:
        order_list = create_cloud_orders(3)
        running = create_cloud_backtest(status="Running", completed=False, progress=0.5)
        screen = await _open_cloud_orders(app, pilot, running, order_list)
        assert screen.query_one("#orders-table").row_count == 3

        order_list.extend(create_cloud_orders(2, first_id=4))
        screen._poll()
        await _settle(app, pilot)

        assert screen.query_one("#orders-table").row_count == 5
        assert _order_requests() == [(0, 100), (3, 103)]

    _run_app(test, logged_in=True)


def test_orders_reload_when_the_backtest_completes() -> None:
    async def test(app: LeanApp, pilot) -> None:
        running = create_cloud_backtest(status="Running", completed=False, progress=0.5)
        screen = await _open_cloud_orders(app, pilot, running, create_cloud_orders(3))

        running.update(create_cloud_backtest())
        screen._poll()
        await _settle(app, pilot)

        assert screen.query_one("#orders-table").row_count == 3
        assert _order_requests()[-1] == (0, 100)
        assert _orders_label(screen) == "Orders (3)"

    _run_app(test, logged_in=True)


def test_orders_that_are_not_readable_yet_are_retried() -> None:
    async def test(app: LeanApp, pilot) -> None:
        backtest = create_cloud_backtest()
        backtest["statistics"]["Total Orders"] = "2"

        # The endpoint returns no orders the first two times it is asked
        order_list = _OrdersAfter(2, create_cloud_orders(2))
        with mock.patch.object(backtest_screen, "ORDERS_RETRY_SECONDS", 0.1):
            screen = await _open_cloud_orders(app, pilot, backtest, order_list)
            for _ in range(10):
                if screen.query_one("#orders-table").row_count:
                    break
                await pilot.pause(0.1)
                await _settle(app, pilot)

        assert screen.query_one("#orders-table").row_count == 2
        assert _orders_label(screen) == "Orders (2)"
        assert len(_order_requests()) == 3

    _run_app(test, logged_in=True)


def test_orders_of_a_running_cloud_backtest_ignore_the_length_without_orders() -> None:
    async def test(app: LeanApp, pilot) -> None:
        running = create_cloud_backtest(status="In Progress...", completed=False, progress=0.26)
        screen = await _open_cloud_orders(app, pilot, running, [])
        serve = container.api_client.post.side_effect

        # The cloud serves a running backtest's orders as an empty list with a length of 100
        container.api_client.post.side_effect = lambda endpoint, payload: \
            {"orders": [], "length": 100, "success": True} if endpoint == "backtests/orders/read" \
            else serve(endpoint, payload)
        screen._poll()
        await _settle(app, pilot)

        assert screen.query_one("#orders-table").row_count == 0
        assert _orders_label(screen) == "Orders (none yet)"

    _run_app(test, logged_in=True)
