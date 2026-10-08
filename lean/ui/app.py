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

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, OptionList, RichLog, Static
from textual.widgets.option_list import Option

from lean.ui.actions import ACTIONS, CLOUD_BACKTEST_URL, CommandProcess, ProjectAction, format_command
from lean.ui.backtest_screen import BacktestScreen, LiveRun
from lean.ui.projects import (UIProject, discover_local_projects, fetch_cloud_projects, filter_projects,
                              is_logged_in, merge_cloud_projects)
from lean.ui.results import BacktestSource, CloudBacktest, LocalBacktest, PendingCloudBacktest


class ProjectTable(DataTable):
    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]


class ActionList(OptionList):
    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]


class ConfirmScreen(ModalScreen[bool]):
    """Shows the command an action is about to run and asks for confirmation."""

    BINDINGS = [
        Binding("y,enter", "confirm", "Run"),
        Binding("n,escape", "cancel", "Cancel"),
    ]

    def __init__(self, command: str) -> None:
        super().__init__()
        self._command = command

    def compose(self) -> ComposeResult:
        message = Text.assemble(("Run this command?\n\n", "bold"), (self._command, "cyan"),
                                ("\n\n", ""), ("y", "bold"), (" / enter to run, ", "dim"),
                                ("n", "bold"), (" / esc to cancel", "dim"))
        yield Static(message, id="confirm")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class LeanApp(App):
    """A keyboard-driven terminal UI for browsing projects and running Lean CLI commands on them."""

    TITLE = "LEAN"

    CSS = """
    #sidebar { width: 2fr; min-width: 32; }
    #main { width: 3fr; }
    #filter { border: round $primary-darken-2; }
    #filter:focus { border: round $accent; }
    ProjectTable, #details, ActionList, #output { border: round $primary-darken-2; }
    ProjectTable:focus, ActionList:focus, #output:focus { border: round $accent; }
    ProjectTable { height: 1fr; overflow-x: hidden; }
    #details { height: auto; padding: 0 1; }
    ActionList { height: auto; max-height: 10; }
    #output { height: 1fr; }
    ConfirmScreen { align: center middle; }
    #confirm { width: auto; max-width: 90%; padding: 1 2; border: round $accent; background: $surface; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("r", "refresh", "Refresh"),
        Binding("x", "stop_command", "Stop command"),
        Binding("escape", "back", "Back", show=False),
    ] + [Binding(a.key, f"run_action('{a.key}')", a.label, show=False) for a in ACTIONS]

    def __init__(self, root: Path, data_dir: Optional[Path] = None) -> None:
        super().__init__()
        self._root = root
        self._data_dir = data_dir
        self._projects: List[UIProject] = []
        self._visible: List[UIProject] = []
        self._logged_in = False
        self._process: Optional[CommandProcess] = None
        self._live_screen: Optional[BacktestScreen] = None

    def _query(self, selector, expect_type=None):
        """Queries the projects screen, which stays at the bottom of the stack while other screens are shown."""
        screen = self.screen_stack[0]
        return screen.query_one(selector, expect_type) if expect_type is not None else screen.query_one(selector)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Input(placeholder="type to filter projects", id="filter")
                yield ProjectTable(cursor_type="row", zebra_stripes=True)
            with Vertical(id="main"):
                yield Static(id="details")
                yield ActionList()
                yield RichLog(id="output", wrap=True, markup=False, min_width=20)
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = str(self._root)

        table = self._query(ProjectTable)
        table.add_columns("Where", "Lang", "Project")
        table.border_title = "Projects"
        self._query("#filter", Input).border_title = "Filter (/)"
        self._query("#details", Static).border_title = "Project"
        self._query(ActionList).border_title = "Actions"
        self._query("#output", RichLog).border_title = "Output"

        table.focus()
        self.action_refresh()

    # Loading projects

    def action_refresh(self) -> None:
        self._load_projects()

    @work(thread=True, exclusive=True, group="projects")
    def _load_projects(self) -> None:
        skip_dirs = [self._data_dir] if self._data_dir is not None else []
        local_projects = discover_local_projects(self._root, skip_dirs)
        logged_in = is_logged_in()
        self.call_from_thread(self._set_projects, local_projects, logged_in,
                              "loading cloud projects..." if logged_in else "not logged in, showing local projects")

        if not logged_in:
            return

        try:
            cloud_projects = fetch_cloud_projects()
        except Exception as exception:
            self.call_from_thread(self._set_projects, local_projects, logged_in, "cloud projects unavailable")
            self.call_from_thread(self.notify, f"Could not load cloud projects: {exception}", severity="error")
            return

        projects = merge_cloud_projects(local_projects, cloud_projects)
        self.call_from_thread(self._set_projects, projects, logged_in, f"{len(cloud_projects)} cloud projects")

    def _set_projects(self, projects: List[UIProject], logged_in: bool, status: str) -> None:
        self._projects = projects
        self._logged_in = logged_in
        self._query(ProjectTable).border_subtitle = status
        self._apply_filter()

    # Filtering and selection

    @on(Input.Changed, "#filter")
    def _filter_changed(self) -> None:
        self._apply_filter()

    @on(Input.Submitted, "#filter")
    def _filter_submitted(self) -> None:
        self._query(ProjectTable).focus()

    def _apply_filter(self) -> None:
        table = self._query(ProjectTable)
        selected = self.selected_project

        self._visible = filter_projects(self._projects, self._query("#filter", Input).value)

        table.clear()
        for index, project in enumerate(self._visible):
            location_style = {"synced": "green", "local": "yellow", "cloud": "cyan"}[project.location]
            name = Text(project.name, style="dim" if project.is_library else "")
            table.add_row(Text(project.location, style=location_style), project.language, name, key=str(index))

        table.border_title = f"Projects ({len(self._visible)}/{len(self._projects)})"

        if selected is not None:
            for index, project in enumerate(self._visible):
                if project.name == selected.name and project.cloud_id == selected.cloud_id:
                    table.move_cursor(row=index)
                    break

        self._show_project(self.selected_project)

    @property
    def selected_project(self) -> Optional[UIProject]:
        table = self._query(ProjectTable)
        if not self._visible or table.cursor_row < 0 or table.cursor_row >= len(self._visible):
            return None
        return self._visible[table.cursor_row]

    @on(DataTable.RowHighlighted)
    def _row_highlighted(self) -> None:
        self._show_project(self.selected_project)

    @on(DataTable.RowSelected)
    def _row_selected(self) -> None:
        self._query(ActionList).focus()

    def _show_project(self, project: Optional[UIProject]) -> None:
        details = self._query("#details", Static)
        actions = self._query(ActionList)
        actions.clear_options()

        if project is None:
            query = self._query("#filter", Input).value
            if self._projects and query:
                message = f"No projects match '{query}'."
            else:
                message = "No projects found. Create one with `lean project-create`."
            details.update(Text(message, style="dim"))
            return

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold")
        grid.add_column()
        grid.add_row("Name", project.name)
        grid.add_row("Location", project.location)
        grid.add_row("Language", project.language or "unknown")
        grid.add_row("Cloud id", str(project.cloud_id) if project.is_cloud else "not in the cloud")
        grid.add_row("Path", str(project.path) if project.is_local else "not pulled")
        if project.modified is not None:
            grid.add_row("Modified", project.modified.strftime("%Y-%m-%d %H:%M"))
        if project.description:
            grid.add_row("Description", project.description)
        details.update(grid)

        for action in ACTIONS:
            reason = action.unavailable_reason(project, self._logged_in)
            prompt = Text.assemble((f" {action.key} ", "bold reverse"), f"  {action.label}")
            if reason is not None:
                prompt.append(f"  ({reason})", style="dim")
            actions.add_option(Option(prompt, id=action.key, disabled=reason is not None))

        available = [i for i, a in enumerate(ACTIONS) if a.unavailable_reason(project, self._logged_in) is None]
        if available:
            actions.highlighted = available[0]

    # Navigation

    def check_action(self, action: str, parameters: tuple) -> Optional[bool]:
        # The project actions belong to the projects screen, other screens use these keys for their own bindings
        if action in ("run_action", "focus_filter", "refresh") and len(self.screen_stack) > 1:
            return False
        return True

    def action_focus_filter(self) -> None:
        self._query("#filter", Input).focus()

    def action_back(self) -> None:
        filter_input = self._query("#filter", Input)
        if filter_input.has_focus and filter_input.value:
            filter_input.value = ""
        self._query(ProjectTable).focus()

    # Running commands

    @on(OptionList.OptionSelected)
    def _action_selected(self, event: OptionList.OptionSelected) -> None:
        self.action_run_action(event.option.id)

    def action_run_action(self, key: str) -> None:
        project = self.selected_project
        action = next(a for a in ACTIONS if a.key == key)
        if project is None:
            return

        reason = action.unavailable_reason(project, self._logged_in)
        if reason is not None:
            self.notify(f"Cannot {action.label.lower()} '{project.name}': {reason}", severity="warning")
            return

        if action.opens_results:
            self.push_screen(BacktestScreen(project, self._logged_in))
            return

        if self._process is not None:
            self.notify("A command is already running, press x to stop it", severity="warning")
            return

        args = action.build_args(project)

        if action.live is not None:
            self._start_backtest(action, project, args)
            return

        def on_confirm(confirmed: Optional[bool]) -> None:
            if confirmed:
                self._run_command(action, args)

        self.push_screen(ConfirmScreen(format_command(args)), on_confirm)

    def _start_backtest(self, action: ProjectAction, project: UIProject, args: List[str]) -> None:
        """Runs a backtest and opens its results, which fill in as the backtest runs."""
        source: BacktestSource
        if action.live == "local":
            # Choosing the output directory lets the results screen read it while the backtest runs
            output_dir = project.path / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            args = args + ["--output", str(output_dir)]
            source = LocalBacktest(output_dir)
        else:
            # The backtest id is known once the command has pushed and compiled the project
            source = PendingCloudBacktest()

        live = LiveRun(source, lines=[f"$ {format_command(args)}"])
        self._live_screen = BacktestScreen(project, self._logged_in, live)
        self.push_screen(self._live_screen)
        self._run_command(action, args)

    @work(thread=True, group="command")
    def _run_command(self, action: ProjectAction, args: List[str]) -> None:
        process = CommandProcess(args, self._root)
        self._process = process
        self.call_from_thread(self._command_started, args)

        try:
            exit_code = process.run(lambda line: self.call_from_thread(self._command_output, line))
        except Exception as exception:
            self.call_from_thread(self._command_output, f"Could not run the command: {exception}")
            exit_code = -1

        self._process = None
        self.call_from_thread(self._command_finished, exit_code, action.refreshes_projects)

    @property
    def _live_screen_shown(self) -> Optional[BacktestScreen]:
        """The results screen of the running backtest, unless it was closed."""
        return self._live_screen if self._live_screen in self.screen_stack else None

    def _command_started(self, args: List[str]) -> None:
        output = self._query("#output", RichLog)
        output.clear()
        output.write(Text(f"$ {format_command(args)}", style="bold cyan"))
        output.border_title = f"Output: {format_command(args)}"
        output.border_subtitle = "running, x to stop"

    def _command_output(self, line: str) -> None:
        self._query("#output", RichLog).write(Text.from_ansi(line))

        live_screen = self._live_screen_shown
        if live_screen is None:
            return
        live_screen.add_live_line(line)
        match = CLOUD_BACKTEST_URL.search(line)
        if match is not None and isinstance(live_screen.live_source, PendingCloudBacktest):
            live_screen.set_live_source(CloudBacktest(int(match.group(1)), match.group(2)))

    def _command_finished(self, exit_code: int, refresh_projects: bool) -> None:
        output = self._query("#output", RichLog)
        output.border_subtitle = "done" if exit_code == 0 else f"failed (exit code {exit_code})"
        output.write(Text(output.border_subtitle, style="green" if exit_code == 0 else "red"))

        live_screen = self._live_screen_shown
        if live_screen is not None:
            live_screen.add_live_line(output.border_subtitle)
            live_screen.live_finished(exit_code)
        self._live_screen = None

        if refresh_projects:
            self.action_refresh()
        else:
            # A finished backtest can make the view action available
            self._show_project(self.selected_project)

    def action_stop_command(self) -> None:
        if self._process is None:
            return
        self._process.stop()
        self._query("#output", RichLog).border_subtitle = "stopping, x again to force"

    async def action_quit(self) -> None:
        if self._process is not None:
            self._process.stop()
        self.exit()
