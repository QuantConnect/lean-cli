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
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.events import Key
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Header, Input, OptionList, RichLog, Static, TabbedContent, TabPane
from textual.widgets.option_list import Option
from textual.worker import get_current_worker
from textual_plotext import PlotextPlot

from lean.ui.projects import UIProject
from lean.ui.results import (ORDERS_PAGE, BacktestResult, BacktestSource, Order, list_cloud_backtests,
                             list_local_backtests, sort_newest_first)
from lean.ui.ticks import format_value_ticks, time_ticks, value_ticks

# Most equity charts are a few hundred points, this keeps rendering fast for long high resolution backtests
MAX_PLOT_POINTS = 2000

# Runtime statistics shown above the chart, in the order the QuantConnect UI shows them
SUMMARY_STATISTICS = ["Equity", "Net Profit", "Return", "Probabilistic Sharpe Ratio", "Unrealized", "Holdings",
                      "Fees", "Volume"]

# The next page of orders loads when the cursor or the scroll position is this many rows from the end
ORDERS_LOAD_MARGIN = 20

# Orders can be readable a little after a cloud backtest completes, until then loading them is retried
ORDERS_RETRY_SECONDS = 10
ORDERS_RETRIES = 6

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
    """The equity of a backtest over time, with dates on the x axis and dollar values on the y axis.

    When the backtest's period is known the x axis spans all of it, so a running backtest's equity grows from left
    to right instead of being stretched over the full width.
    """

    def __init__(self, *, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._points: Sequence[Tuple[float, float]] = []
        self._period: Optional[Tuple[float, float]] = None
        self._message = "No data"

    @property
    def points(self) -> Sequence[Tuple[float, float]]:
        return self._points

    @property
    def x_range(self) -> Optional[Tuple[float, float]]:
        """The times the x axis spans, or None without points."""
        if not self._points:
            return None
        low, high = self._points[0][0], self._points[-1][0]
        if self._period is not None:
            low, high = min(low, self._period[0]), max(high, self._period[1])
        return low, high

    def set_points(self, points: Sequence[Tuple[float, float]], message: str = "No data",
                   period: Optional[Tuple[datetime, datetime]] = None) -> None:
        """Sets the equity points, and the start and end of the backtest if known."""
        self._points = _downsample(points)
        self._period = (period[0].timestamp(), period[1].timestamp()) if period is not None else None
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
        x_low, x_high = self.x_range
        if x_high > x_low:
            plt.xlim(x_low, x_high)
        x_ticks, x_labels = time_ticks(x_low, x_high, max(2, self.size.width // 16))
        plt.xticks(x_ticks, x_labels)

        self.refresh()


class OrdersTable(DataTable):
    """The orders of a backtest, which asks for more orders when the cursor or scroll position nears the end."""

    class NearEnd(Message):
        pass

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        self._check_near_end()

    def watch_cursor_coordinate(self, old_coordinate, new_coordinate) -> None:
        super().watch_cursor_coordinate(old_coordinate, new_coordinate)
        self._check_near_end()

    @property
    def near_end(self) -> bool:
        """Whether the cursor or the bottom of the view is close to the last row."""
        if self.row_count == 0:
            return False
        # Measured in rows, as the scroll limits are not updated yet when rows have just been added
        last_visible_row = int(self.scroll_y) + self.size.height
        return max(last_visible_row, self.cursor_row) >= self.row_count - ORDERS_LOAD_MARGIN

    def _check_near_end(self) -> None:
        if self.near_end:
            self.post_message(self.NearEnd())


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
        self._log_loaded_for: Optional[str] = None
        self._poll_timer: Optional[Timer] = None

        # Orders are loaded a page at a time as they are scrolled to
        self._orders_for: Optional[str] = None
        self._orders_count = 0
        self._orders_total: Optional[int] = None
        self._orders_loading = False
        self._orders_retries = 0

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
                    yield OrdersTable(id="orders-table", cursor_type="row", zebra_stripes=True)
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
        self._reset_orders()
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
        self._log_loaded_for = None
        self._reset_orders()
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
        self._load_result(backtest, load_log=tab == "logs" and not self._is_live(backtest))

    @work(thread=True, exclusive=True, group="result")
    def _load_result(self, backtest: BacktestSource, load_log: bool) -> None:
        worker = get_current_worker()
        error = None
        result = log = None
        try:
            result = backtest.load()
            if load_log:
                log = backtest.load_log()
        except Exception as exception:
            error = exception
        if not worker.is_cancelled:
            self.app.call_from_thread(self._show_result, backtest, result, log, error)

    def _show_result(self, backtest: BacktestSource, result: Optional[BacktestResult], log: Optional[List[str]],
                     error: Optional[Exception]) -> None:
        if backtest is not self.backtest:
            return
        if error is not None:
            self.notify(f"Could not load the backtest: {error}", severity="error")
        just_finished = False
        if result is not None:
            just_finished = self._result is not None and not self._result.finished
            self._result = result
            self._apply_live_exit()
            just_finished = just_finished and self._result.finished
        self._show_summary()
        self._show_chart()
        self._show_statistics()
        if log is not None:
            self._show_log(log)
            self._log_loaded_for = backtest.id

        if just_finished:
            # Orders loaded while running may have changed status, so load them again
            self._reset_orders()
        self._update_orders()

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
        if not self._is_live(self.backtest):
            self._log_loaded_for = None
        self._load()

    @on(TabbedContent.TabActivated)
    def _tab_activated(self, event: TabbedContent.TabActivated) -> None:
        backtest = self.backtest
        if backtest is None:
            return
        if event.pane.id == "orders":
            self._update_orders()
        elif event.pane.id == "logs" and self._log_loaded_for != backtest.id:
            self._load()

    # Loading orders a page at a time

    def _reset_orders(self) -> None:
        self._orders_for = None
        self._orders_count = 0
        self._orders_total = None
        self._orders_retries = 0
        self.query_one("#orders-table", OrdersTable).clear()
        self._label_orders()

    def _update_orders(self) -> None:
        """Loads the first page of orders when the tab is shown, and new orders while the backtest runs."""
        backtest = self.backtest
        if backtest is None or self.query_one(TabbedContent).active != "orders":
            return
        if self._orders_for != backtest.id:
            self._reset_orders()
            self._orders_for = backtest.id
            self._load_more_orders()
        elif self._result is not None and not self._result.finished:
            # Ask for any orders the running backtest has placed since the last refresh
            self._load_more_orders(new_orders=True)

    @on(OrdersTable.NearEnd)
    def _near_end_of_orders(self) -> None:
        # Checked again, as the message may have been posted while the table was still filling
        if self.query_one("#orders-table", OrdersTable).near_end:
            self._load_more_orders()

    def _load_more_orders(self, new_orders: bool = False) -> None:
        """Loads the next page of orders, if there are more or new_orders asks to check for new ones."""
        backtest = self.backtest
        if backtest is None or self._orders_for != backtest.id or self._orders_loading:
            return
        if not new_orders and self._orders_total is not None and self._orders_count >= self._orders_total:
            return
        self._orders_loading = True
        self._label_orders()
        self._load_orders_page(backtest, self._orders_count)

    @work(thread=True, group="orders")
    def _load_orders_page(self, backtest: BacktestSource, start: int) -> None:
        try:
            orders, total = backtest.load_orders(start, start + ORDERS_PAGE)
            error = None
        except Exception as exception:
            orders, total, error = [], None, exception
        self.app.call_from_thread(self._add_orders, backtest, start, orders, total, error)

    def _add_orders(self, backtest: BacktestSource, start: int, orders: List[Order], total: Optional[int],
                    error: Optional[Exception]) -> None:
        self._orders_loading = False
        self._label_orders()
        if backtest is not self.backtest or self._orders_for != backtest.id or start != self._orders_count:
            # The table was reset while this page loaded
            if self._orders_for == getattr(self.backtest, "id", None):
                self._load_more_orders()
            return
        if error is not None:
            self.notify(f"Could not load orders: {error}", severity="error")
            return

        self._show_orders(orders)
        self._orders_count += len(orders)
        self._orders_total = max(total or 0, self._orders_count)
        self._label_orders()

        if self._orders_total == 0 and self._orders_expected() and self._orders_retries < ORDERS_RETRIES:
            self._orders_retries += 1
            self.set_timer(ORDERS_RETRY_SECONDS, self._retry_orders)

    def _orders_expected(self) -> bool:
        """Whether the statistics count orders that the orders endpoint does not return yet."""
        result = self._result
        if result is None or not result.finished:
            return False
        try:
            return int(result.statistics.get("Total Orders", "0").replace(",", "")) > 0
        except ValueError:
            return False

    def _retry_orders(self) -> None:
        backtest = self.backtest
        if backtest is not None and self._orders_for == backtest.id and self._orders_count == 0:
            self._orders_total = None
            self._load_more_orders()

    def _label_orders(self) -> None:
        if self._orders_loading and self._orders_count == 0:
            label = "Orders (loading...)"
        elif self._orders_total is None:
            label = "Orders"
        elif self._orders_count < self._orders_total:
            label = f"Orders ({self._orders_count:,} of {self._orders_total:,})"
        else:
            label = f"Orders ({self._orders_total:,})"
        self.query_one(TabbedContent).get_tab("orders").label = label

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
        period = (result.start, result.end) if result is not None and result.start and result.end else None
        self.query_one("#equity", EquityChart).set_points(result.equity if result is not None else [], message,
                                                          period)

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
        table = self.query_one("#orders-table", OrdersTable)
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

    def _show_log(self, lines: List[str]) -> None:
        log = self.query_one("#log", RichLog)
        log.clear()
        log.write("\n".join(lines) if lines else Text("No log lines", style="dim"))
