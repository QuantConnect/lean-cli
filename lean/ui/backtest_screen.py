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

from dataclasses import dataclass, field
from datetime import timezone
from typing import List, Optional, Sequence, Tuple

from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Header, Input, OptionList, RichLog, Static, TabbedContent, TabPane
from textual.widgets.option_list import Option
from textual.worker import get_current_worker
from textual_plotext import PlotextPlot

from lean.ui.projects import UIProject
from lean.ui.results import (BacktestResult, BacktestSource, Order, list_cloud_backtests, list_local_backtests,
                             sort_newest_first)
from lean.ui.ticks import format_value_ticks, time_ticks, value_ticks

# Most equity charts are a few hundred points, this keeps rendering fast for long high resolution backtests
MAX_PLOT_POINTS = 2000

# Runtime statistics shown above the chart, in the order the QuantConnect UI shows them
SUMMARY_STATISTICS = ["Equity", "Net Profit", "Return", "Probabilistic Sharpe Ratio", "Unrealized", "Holdings",
                      "Fees", "Volume"]

# Statistics where a negative value is bad and a positive value is good
SIGNED_STATISTICS = {"Net Profit", "Return", "Unrealized", "Compounding Annual Return", "Sharpe Ratio",
                     "Sortino Ratio", "Alpha", "Expectancy", "Information Ratio", "Treynor Ratio"}


def _downsample(points: Sequence[Tuple[float, float]]) -> Sequence[Tuple[float, float]]:
    if len(points) <= MAX_PLOT_POINTS:
        return points
    step = len(points) / MAX_PLOT_POINTS
    return [points[int(i * step)] for i in range(MAX_PLOT_POINTS)] + [points[-1]]


def _style_statistic(name: str, value: str) -> Text:
    if name in SIGNED_STATISTICS and value:
        return Text(value, style="red" if value.lstrip("$").startswith("-") else "green")
    return Text(value)


def _format_created(source: BacktestSource) -> str:
    created = source.created
    return created.astimezone().strftime("%Y-%m-%d %H:%M") if created is not None else ""


@dataclass
class LiveRun:
    """A backtest the UI started, whose command output is shown as its log."""

    source: BacktestSource
    lines: List[str] = field(default_factory=list)
    exit_code: Optional[int] = None


class EquityChart(PlotextPlot):
    """The equity of a backtest over time, with dates on the x axis and dollar values on the y axis."""

    def __init__(self, *, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._points: Sequence[Tuple[float, float]] = []
        self._message = "No data"

    @property
    def points(self) -> Sequence[Tuple[float, float]]:
        return self._points

    def set_points(self, points: Sequence[Tuple[float, float]], message: str = "No data") -> None:
        self._points = _downsample(points)
        self._message = message
        self._replot()

    def on_resize(self) -> None:
        self._replot()

    def _replot(self) -> None:
        plt = self.plt
        plt.clear_figure()

        if not self._points:
            plt.title(self._message)
            self.refresh()
            return

        xs = [x for x, _ in self._points]
        ys = [y for _, y in self._points]
        plt.plot(xs, ys, color="cyan", marker="braille")

        y_ticks, y_step = value_ticks(min(ys), max(ys), max(3, min(8, self.size.height // 2)))
        plt.yticks(y_ticks, format_value_ticks(y_ticks, y_step, "$"))
        x_ticks, x_labels = time_ticks(min(xs), max(xs), max(2, self.size.width // 16))
        plt.xticks(x_ticks, x_labels)

        self.refresh()


class BacktestPicker(ModalScreen[Optional[int]]):
    """Lists a project's backtests, local and cloud, to pick one to show."""

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel")]

    DEFAULT_CSS = """
    BacktestPicker { align: center middle; }
    BacktestPicker > Vertical { width: 90; max-width: 95%; height: 80%; border: round $accent; background: $surface; }
    BacktestPicker OptionList { height: 1fr; border: none; }
    """

    def __init__(self, backtests: List[BacktestSource], selected: int) -> None:
        super().__init__()
        self._backtests = backtests
        self._selected = selected

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(placeholder="type to filter backtests")
            yield OptionList()

    def on_mount(self) -> None:
        self.query_one(Vertical).border_title = f"Backtests ({len(self._backtests)})"
        self._fill("")
        self.query_one(Input).focus()

    def _fill(self, query: str) -> None:
        options = self.query_one(OptionList)
        options.clear_options()
        words = query.casefold().split()
        for index, backtest in enumerate(self._backtests):
            if all(w in f"{backtest.name} {backtest.location}".casefold() for w in words):
                options.add_option(Option(Text.assemble(
                    (f"{backtest.location:<6}", "cyan" if backtest.location == "cloud" else "yellow"), "  ",
                    (f"{_format_created(backtest):<17}", "dim"), "  ", backtest.name), id=str(index)))
        ids = [options.get_option_at_index(i).id for i in range(options.option_count)]
        if ids:
            options.highlighted = ids.index(str(self._selected)) if str(self._selected) in ids else 0

    @on(Input.Changed)
    def _filter_changed(self, event: Input.Changed) -> None:
        self._fill(event.value)

    @on(Input.Submitted)
    def _filter_submitted(self) -> None:
        options = self.query_one(OptionList)
        if options.highlighted is not None:
            self.dismiss(int(options.get_option_at_index(options.highlighted).id))

    def on_key(self, event: Key) -> None:
        # The arrow keys move through the list while typing in the filter
        if event.key in ("up", "down"):
            options = self.query_one(OptionList)
            if event.key == "up":
                options.action_cursor_up()
            else:
                options.action_cursor_down()
            event.stop()

    @on(OptionList.OptionSelected)
    def _option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(int(event.option.id))


class BacktestScreen(Screen):
    """Shows a project's backtest results like the QuantConnect.com backtest page, refreshing while they change."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("o", "pick_backtest", "Backtests"),
        Binding("left_square_bracket", "step_backtest(-1)", "Newer"),
        Binding("right_square_bracket", "step_backtest(1)", "Older"),
        Binding("r", "reload", "Reload"),
        Binding("1", "show_tab('statistics')", "Statistics"),
        Binding("2", "show_tab('orders')", "Orders"),
        Binding("3", "show_tab('logs')", "Logs"),
    ]

    DEFAULT_CSS = """
    BacktestScreen #summary, BacktestScreen EquityChart, BacktestScreen TabbedContent {
        border: round $primary-darken-2;
    }
    BacktestScreen #summary { height: auto; padding: 0 1; }
    BacktestScreen EquityChart { height: 1fr; min-height: 10; }
    BacktestScreen TabbedContent { height: 1fr; min-height: 10; }
    BacktestScreen #statistics-scroll { height: 1fr; }
    """

    def __init__(self, project: UIProject, logged_in: bool, live: Optional[LiveRun] = None) -> None:
        super().__init__()
        self._project = project
        self._logged_in = logged_in
        self._live = live
        self._backtests: List[BacktestSource] = [live.source] if live is not None else []
        self._selected = 0
        self._result: Optional[BacktestResult] = None
        self._orders_loaded_for: Optional[str] = None
        self._log_loaded_for: Optional[str] = None
        self._poll_timer: Optional[Timer] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(id="summary")
            yield EquityChart(id="equity")
            with TabbedContent(initial="statistics"):
                with TabPane("Statistics", id="statistics"):
                    with VerticalScroll(id="statistics-scroll"):
                        yield Static(id="statistics-table")
                with TabPane("Orders", id="orders"):
                    yield DataTable(id="orders-table", cursor_type="row", zebra_stripes=True)
                with TabPane("Logs", id="logs"):
                    yield RichLog(id="log", markup=False, min_width=20)
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self._project.name
        self.query_one("#equity", EquityChart).border_title = "Strategy Equity"
        self.query_one("#orders-table", DataTable).add_columns(
            "ID", "Time (UTC)", "Symbol", "Type", "Side", "Quantity", "Price", "Value", "Status", "Tag")
        if self._live is not None:
            # Show what the command prints while the backtest starts
            self.query_one(TabbedContent).active = "logs"
        self._show_backtest()
        self._list_backtests()

    # The list of backtests

    @property
    def backtest(self) -> Optional[BacktestSource]:
        return self._backtests[self._selected] if self._backtests else None

    @property
    def result(self) -> Optional[BacktestResult]:
        return self._result

    @work(thread=True, exclusive=True, group="list")
    def _list_backtests(self) -> None:
        backtests: List[BacktestSource] = list(list_local_backtests(self._project.path))
        error = None
        if self._project.is_cloud and self._logged_in:
            try:
                backtests.extend(list_cloud_backtests(self._project.cloud_id))
            except Exception as exception:
                error = exception
        self.app.call_from_thread(self._set_backtests, sort_newest_first(backtests), error)

    def _set_backtests(self, backtests: List[BacktestSource], error: Optional[Exception]) -> None:
        if error is not None:
            self.notify(f"Could not load cloud backtests: {error}", severity="error")

        current = self.backtest
        if self._live is not None:
            # The backtest being run stays first, the listing may not include it yet
            backtests = [self._live.source] + [b for b in backtests if b.id != self._live.source.id]
        self._backtests = backtests

        if current is not None and any(b.id == current.id for b in backtests):
            # Keep showing the same backtest, and the object already holding its results
            self._selected = next(i for i, b in enumerate(backtests) if b.id == current.id)
            self._backtests[self._selected] = current
            self._update_position()
        else:
            self._selected = 0
            self._show_backtest()

    def action_pick_backtest(self) -> None:
        if not self._backtests:
            return

        def picked(index: Optional[int]) -> None:
            if index is not None and index != self._selected:
                self._selected = index
                self._show_backtest()

        self.app.push_screen(BacktestPicker(self._backtests, self._selected), picked)

    def action_step_backtest(self, step: int) -> None:
        index = self._selected + step
        if 0 <= index < len(self._backtests):
            self._selected = index
            self._show_backtest()

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_reload(self) -> None:
        self._orders_loaded_for = None
        if not self._is_live(self.backtest):
            self._log_loaded_for = None
        self._load()

    # The backtest the UI is running

    def set_live_source(self, source: BacktestSource) -> None:
        """Replaces the backtest being run, once a new cloud backtest has an id."""
        if self._live is None:
            return
        was_selected = self._is_live(self.backtest)
        old_source = self._live.source
        self._live.source = source
        self._backtests = [source] + [b for b in self._backtests if b is not old_source and b.id != source.id]
        if was_selected:
            self._selected = 0
            self._result = None
            self._update_position()
            self._load()
        else:
            self._selected = next((i for i, b in enumerate(self._backtests) if b is self.backtest), 0)

    def add_live_line(self, line: str) -> None:
        if self._live is None:
            return
        self._live.lines.append(line)
        if self._is_live(self.backtest):
            self.query_one("#log", RichLog).write(Text.from_ansi(line))

    def live_finished(self, exit_code: int) -> None:
        if self._live is None:
            return
        self._live.exit_code = exit_code
        if self._is_live(self.backtest):
            self._load()

    @property
    def live_source(self) -> Optional[BacktestSource]:
        return self._live.source if self._live is not None else None

    def _is_live(self, source: Optional[BacktestSource]) -> bool:
        return self._live is not None and source is not None and source is self._live.source

    # Loading results

    def _show_backtest(self) -> None:
        self._result = None
        self._orders_loaded_for = None
        self._log_loaded_for = None
        self.query_one("#orders-table", DataTable).clear()
        self.query_one(TabbedContent).get_tab("orders").label = "Orders"
        log = self.query_one("#log", RichLog)
        log.clear()
        if self._is_live(self.backtest):
            for line in self._live.lines:
                log.write(Text.from_ansi(line))
            self._log_loaded_for = self.backtest.id

        self._update_position()
        self._show_summary()
        self._show_chart()
        self._show_statistics()
        self._load()

    def _update_position(self) -> None:
        summary = self.query_one("#summary", Static)
        summary.border_subtitle = f"{self._selected + 1}/{len(self._backtests)}  [ ] newer/older, o all" \
            if self._backtests else ""

    def _load(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.stop()
            self._poll_timer = None
        backtest = self.backtest
        if backtest is None:
            self._show_summary()
            return
        tab = self.query_one(TabbedContent).active
        self._load_result(backtest,
                          load_orders=tab == "orders",
                          load_log=tab == "logs" and not self._is_live(backtest))

    @work(thread=True, exclusive=True, group="result")
    def _load_result(self, backtest: BacktestSource, load_orders: bool, load_log: bool) -> None:
        worker = get_current_worker()
        error = None
        result = orders = log = None
        try:
            result = backtest.load()
            if load_orders:
                orders = backtest.load_orders()
            if load_log:
                log = backtest.load_log()
        except Exception as exception:
            error = exception
        if not worker.is_cancelled:
            self.app.call_from_thread(self._show_result, backtest, result, orders, log, error)

    def _show_result(self, backtest: BacktestSource, result: Optional[BacktestResult], orders: Optional[List[Order]],
                     log: Optional[List[str]], error: Optional[Exception]) -> None:
        if backtest is not self.backtest:
            return
        if error is not None:
            self.notify(f"Could not load the backtest: {error}", severity="error")
        if result is not None:
            self._result = result
            self._apply_live_exit()
        self._show_summary()
        self._show_chart()
        self._show_statistics()
        if orders is not None:
            self._show_orders(orders)
            self._orders_loaded_for = backtest.id
        if log is not None:
            self._show_log(log)
            self._log_loaded_for = backtest.id

        if self._should_poll():
            self._poll_timer = self.set_timer(backtest.poll_seconds, self._poll)

    def _apply_live_exit(self) -> None:
        # A local run that was stopped leaves its status at Running, the end of the command ends it
        if self._is_live(self.backtest) and self._live.exit_code is not None and self.backtest.location == "local":
            self._result.finished = True

    def _should_poll(self) -> bool:
        if self._result is not None:
            return not self._result.finished
        # Without results keep waiting while the backtest is being started
        return self._is_live(self.backtest) and self._live.exit_code is None

    def _poll(self) -> None:
        self._orders_loaded_for = None
        if not self._is_live(self.backtest):
            self._log_loaded_for = None
        self._load()

    @on(TabbedContent.TabActivated)
    def _tab_activated(self, event: TabbedContent.TabActivated) -> None:
        backtest = self.backtest
        if backtest is None:
            return
        tab = event.pane.id
        if (tab == "orders" and self._orders_loaded_for != backtest.id) or \
                (tab == "logs" and self._log_loaded_for != backtest.id):
            self._load()

    # Rendering

    def _status(self) -> str:
        result = self._result
        live = self._live if self._is_live(self.backtest) else None
        if result is None:
            if live is not None and live.exit_code not in (None, 0):
                return f"failed (exit code {live.exit_code}), see Logs"
            if live is not None and live.exit_code is None:
                return "starting, see Logs" if self.backtest.location == "local" else "pushing and compiling, see Logs"
            return "loading..."
        status = result.status or "Running"
        if not result.finished and result.progress is not None:
            status = f"{status} {result.progress:.0%}"
        return status

    def _show_summary(self) -> None:
        summary = self.query_one("#summary", Static)
        backtest = self.backtest
        if backtest is None:
            summary.border_title = "No backtests"
            summary.update(Text("This project has no backtests yet. Press escape, then b or c to run one.",
                                style="dim"))
            return

        name = self._result.name if self._result is not None and self._result.name else backtest.name
        summary.border_title = f"{name} ({backtest.location}): {self._status()}"

        result = self._result
        if result is None or not result.runtime_statistics:
            summary.update(Text("Waiting for results...", style="dim"))
            return

        grid = Table.grid(padding=(0, 3), expand=True)
        names = [n for n in SUMMARY_STATISTICS if n in result.runtime_statistics]
        for _ in names:
            grid.add_column()
        grid.add_row(*[Text("PSR" if n == "Probabilistic Sharpe Ratio" else n, style="dim") for n in names])
        grid.add_row(*[_style_statistic(n, result.runtime_statistics[n]) for n in names])
        if result.runtime_error:
            grid.add_row(Text(result.runtime_error, style="bold red"))
        summary.update(grid)

    def _show_chart(self) -> None:
        result = self._result
        message = "Waiting for results..." if result is None or not result.finished else "No equity data"
        self.query_one("#equity", EquityChart).set_points(result.equity if result is not None else [], message)

    def _show_statistics(self) -> None:
        table = self.query_one("#statistics-table", Static)
        result = self._result
        if result is None or not (result.statistics or result.parameters):
            table.update(Text("Statistics are available when the backtest completes.", style="dim"))
            return

        grid = Table.grid(padding=(0, 2), expand=True)
        for style in ["dim", None, "dim", None]:
            grid.add_column(style=style)
        items = list(result.statistics.items())
        half = (len(items) + 1) // 2
        for left, right in zip(items[:half], items[half:] + [("", "")]):
            grid.add_row(left[0], _style_statistic(*left), right[0], _style_statistic(*right))
        if result.parameters:
            grid.add_row("", "", "", "")
            grid.add_row(Text("Parameters", style="bold"), "", "", "")
            for name, value in result.parameters.items():
                grid.add_row(name, str(value), "", "")
        table.update(grid)

    def _show_orders(self, orders: List[Order]) -> None:
        table = self.query_one("#orders-table", DataTable)
        table.clear()
        for order in orders:
            table.add_row(str(order.id),
                          order.time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if order.time else "",
                          order.symbol,
                          order.type,
                          Text(order.direction, style="green" if order.direction == "Buy" else "red"),
                          f"{order.quantity:,.6g}",
                          f"{order.price:,.2f}",
                          f"{order.value:,.2f}",
                          order.status,
                          order.tag)
        self.query_one(TabbedContent).get_tab("orders").label = f"Orders ({len(orders)})"

    def _show_log(self, lines: List[str]) -> None:
        log = self.query_one("#log", RichLog)
        log.clear()
        log.write("\n".join(lines) if lines else Text("No log lines", style="dim"))
