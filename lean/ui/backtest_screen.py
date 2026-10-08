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

from typing import List, NamedTuple, Optional, Sequence, Tuple

from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, OptionList, RichLog, Static, TabbedContent, TabPane
from textual.widgets.option_list import Option
from textual.worker import get_current_worker
from textual_plotext import PlotextPlot

from lean.ui.results import BacktestResult, LocalBacktest, Series
from lean.ui.ticks import format_value_ticks, time_ticks, value_ticks

# Most charts are a few hundred points, this keeps rendering fast for long high resolution backtests
MAX_PLOT_POINTS = 2000

# Runtime statistics shown above the charts, in the order the QuantConnect UI shows them
SUMMARY_STATISTICS = ["Equity", "Net Profit", "Return", "Probabilistic Sharpe Ratio", "Unrealized", "Holdings",
                      "Fees", "Volume"]

# Statistics where a negative value is bad and a positive value is good
SIGNED_STATISTICS = {"Net Profit", "Return", "Unrealized", "Compounding Annual Return", "Sharpe Ratio",
                     "Sortino Ratio", "Alpha", "Expectancy", "Information Ratio", "Treynor Ratio"}

SERIES_COLORS = ["cyan", "orange", "magenta", "green", "blue", "yellow", "red", "white"]


def _downsample(points: Sequence[Tuple[float, float]]) -> Sequence[Tuple[float, float]]:
    if len(points) <= MAX_PLOT_POINTS:
        return points
    step = len(points) / MAX_PLOT_POINTS
    sampled = [points[int(i * step)] for i in range(MAX_PLOT_POINTS)]
    return sampled + [points[-1]]


def _style_statistic(name: str, value: str) -> Text:
    if name in SIGNED_STATISTICS and value:
        return Text(value, style="red" if value.lstrip("$").startswith("-") else "green")
    return Text(value)


class Line(NamedTuple):
    label: str
    points: Sequence[Tuple[float, float]]
    color: str
    unit: str = ""


class TimeSeriesChart(PlotextPlot):
    """A line chart of one or more series over time, with dates on the x axis and compact values on the y axis.

    Lines with the same unit as the first line use the left axis, lines in another unit use the right axis.
    """

    def __init__(self, *, fill: bool = False, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._fill = fill
        self._lines: List[Line] = []

    def set_lines(self, lines: List[Line]) -> None:
        self._lines = [line._replace(points=_downsample(line.points)) for line in lines if line.points]
        self._replot()

    def on_resize(self) -> None:
        self._replot()

    def _replot(self) -> None:
        plt = self.plt
        plt.clear_figure()

        if not self._lines:
            plt.title("No data")
            self.refresh()
            return

        left_unit = self._lines[0].unit
        sides = {"left": [line for line in self._lines if line.unit == left_unit],
                 "right": [line for line in self._lines if line.unit != left_unit]}

        for side, lines in sides.items():
            for line in lines:
                plt.plot([x for x, _ in line.points], [y for _, y in line.points],
                         label=line.label if len(self._lines) > 1 else None,
                         color=line.color, marker="braille", fillx=self._fill, yside=side)
            if lines:
                y_values = [y for line in lines for _, y in line.points]
                y_ticks, y_step = value_ticks(min(y_values), max(y_values), max(3, min(8, self.size.height // 2)))
                units = {line.unit for line in lines}
                plt.yticks(y_ticks, format_value_ticks(y_ticks, y_step, units.pop() if len(units) == 1 else ""),
                           yside=side)

        all_x = [x for line in self._lines for x, _ in line.points]
        x_ticks, x_labels = time_ticks(min(all_x), max(all_x), max(2, self.size.width // 16))
        plt.xticks(x_ticks, x_labels)

        self.refresh()


class BacktestScreen(Screen):
    """Shows the results of a project's local backtests, like the backtest results page on QuantConnect.com."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "reload", "Reload"),
        Binding("j", "next_backtest", show=False),
        Binding("k", "previous_backtest", show=False),
        Binding("1", "show_tab('statistics')", "Statistics"),
        Binding("2", "show_tab('orders')", "Orders"),
        Binding("3", "show_tab('charts')", "Charts"),
        Binding("4", "show_tab('logs')", "Logs"),
    ]

    DEFAULT_CSS = """
    BacktestScreen #bt-sidebar { width: 26; }
    BacktestScreen #backtests, BacktestScreen #summary, BacktestScreen TimeSeriesChart, BacktestScreen TabbedContent {
        border: round $primary-darken-2;
    }
    BacktestScreen #backtests:focus { border: round $accent; }
    BacktestScreen #backtests { height: 1fr; }
    BacktestScreen #summary { height: auto; padding: 0 1; }
    BacktestScreen #equity { height: 1fr; min-height: 10; }
    BacktestScreen #drawdown { height: 9; }
    BacktestScreen TabbedContent { height: 1fr; min-height: 10; }
    BacktestScreen #chart-names { width: 28; height: 1fr; }
    BacktestScreen #chart { height: 1fr; border: none; }
    BacktestScreen #statistics-scroll { height: 1fr; }
    """

    def __init__(self, project_name: str, backtests: List[LocalBacktest], selected: int = 0) -> None:
        super().__init__()
        self._project_name = project_name
        self._backtests = backtests
        self._selected = selected
        self._result: Optional[BacktestResult] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="bt-sidebar"):
                yield OptionList(*[Option(b.name, id=str(i)) for i, b in enumerate(self._backtests)], id="backtests")
            with Vertical():
                yield Static(id="summary")
                yield TimeSeriesChart(id="equity")
                yield TimeSeriesChart(fill=True, id="drawdown")
                with TabbedContent(initial="statistics"):
                    with TabPane("Statistics", id="statistics"):
                        with VerticalScroll(id="statistics-scroll"):
                            yield Static(id="statistics-table")
                    with TabPane("Orders", id="orders"):
                        yield DataTable(id="orders-table", cursor_type="row", zebra_stripes=True)
                    with TabPane("Charts", id="charts"):
                        with Horizontal():
                            yield OptionList(id="chart-names")
                            yield TimeSeriesChart(id="chart")
                    with TabPane("Logs", id="logs"):
                        yield RichLog(id="log", markup=False, min_width=20)
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self._project_name
        self.query_one("#backtests", OptionList).border_title = "Backtests"
        self.query_one("#equity", TimeSeriesChart).border_title = "Strategy Equity"
        self.query_one("#drawdown", TimeSeriesChart).border_title = "Drawdown"
        self.query_one("#orders-table", DataTable).add_columns(
            "ID", "Time (UTC)", "Symbol", "Type", "Side", "Quantity", "Price", "Value", "Status", "Tag")

        backtests = self.query_one("#backtests", OptionList)
        backtests.highlighted = self._selected
        backtests.focus()
        self._load()

    # Selecting backtests

    @property
    def backtest(self) -> LocalBacktest:
        return self._backtests[self._selected]

    @on(OptionList.OptionHighlighted, "#backtests")
    def _backtest_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_index != self._selected:
            self._selected = event.option_index
            self._load()

    def action_next_backtest(self) -> None:
        self.query_one("#backtests", OptionList).action_cursor_down()

    def action_previous_backtest(self) -> None:
        self.query_one("#backtests", OptionList).action_cursor_up()

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_reload(self) -> None:
        self._load()

    # Loading results

    def _load(self) -> None:
        self.query_one("#summary", Static).border_title = f"{self.backtest.name}: loading..."
        self._load_result(self.backtest)

    @work(thread=True, exclusive=True, group="backtest")
    def _load_result(self, backtest: LocalBacktest) -> None:
        result = backtest.load()
        log_lines = backtest.log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-2000:] \
            if backtest.log_file.is_file() else []
        if not get_current_worker().is_cancelled:
            self.app.call_from_thread(self._show_result, backtest, result, log_lines)

    def _show_result(self, backtest: LocalBacktest, result: Optional[BacktestResult], log_lines: List[str]) -> None:
        self._result = result
        self._show_summary(backtest, result)
        self._show_charts(result)
        self._show_statistics(result)
        self._show_orders(result)
        self._show_chart_names(result)
        log = self.query_one("#log", RichLog)
        log.clear()
        log.write("\n".join(log_lines) if log_lines else Text("No log file", style="dim"))

    def _show_summary(self, backtest: LocalBacktest, result: Optional[BacktestResult]) -> None:
        summary = self.query_one("#summary", Static)
        if result is None:
            summary.border_title = backtest.name
            summary.update(Text("No results found in this backtest's directory.", style="dim"))
            return

        status = result.status or "Running"
        progress = result.progress
        if status != "Completed" and progress is not None:
            status = f"{status} {progress:.0%}"
        summary.border_title = f"{backtest.name}: {status}"

        grid = Table.grid(padding=(0, 3), expand=True)
        names = [n for n in SUMMARY_STATISTICS if n in result.runtime_statistics]
        for _ in names:
            grid.add_column()
        grid.add_row(*[Text("PSR" if n == "Probabilistic Sharpe Ratio" else n, style="dim") for n in names])
        grid.add_row(*[_style_statistic(n, result.runtime_statistics[n]) for n in names])
        if result.runtime_error:
            grid.add_row(Text(result.runtime_error, style="bold red"))
        summary.update(grid)

    def _show_charts(self, result: Optional[BacktestResult]) -> None:
        equity_chart = self.query_one("#equity", TimeSeriesChart)
        drawdown_chart = self.query_one("#drawdown", TimeSeriesChart)
        equity = result.equity if result is not None else None
        if equity is None:
            equity_chart.set_lines([])
            drawdown_chart.set_lines([])
            return

        lines = [Line("Equity", equity.points, "cyan", "$")]
        benchmark = result.benchmark
        if benchmark is not None and benchmark.points and equity.points and benchmark.points[0][1]:
            # Scale the benchmark to start at the starting equity so both are comparable
            scale = equity.points[0][1] / benchmark.points[0][1]
            lines.append(Line("Benchmark", [(x, y * scale) for x, y in benchmark.points], "gray", "$"))
        equity_chart.set_lines(lines)

        drawdown = result.drawdown
        drawdown_chart.set_lines([Line("Drawdown", drawdown.points, "red", "%")] if drawdown else [])

    def _show_statistics(self, result: Optional[BacktestResult]) -> None:
        table = self.query_one("#statistics-table", Static)
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
                grid.add_row(name, value, "", "")
        table.update(grid)

    def _show_orders(self, result: Optional[BacktestResult]) -> None:
        table = self.query_one("#orders-table", DataTable)
        table.clear()
        if result is None:
            return
        for order in result.orders:
            table.add_row(str(order.id),
                          order.time.strftime("%Y-%m-%d %H:%M:%S") if order.time else "",
                          order.symbol,
                          order.type,
                          Text(order.direction, style="green" if order.direction == "Buy" else "red"),
                          f"{order.quantity:,.6g}",
                          f"{order.price:,.2f}",
                          f"{order.value:,.2f}",
                          order.status,
                          order.tag)
        self.query_one(TabbedContent).get_tab("orders").label = f"Orders ({len(result.orders)})"

    def _show_chart_names(self, result: Optional[BacktestResult]) -> None:
        names = self.query_one("#chart-names", OptionList)
        previous = names.highlighted_option.id if names.highlighted_option is not None else None
        names.clear_options()
        if result is None or not result.charts:
            self.query_one("#chart", TimeSeriesChart).set_lines([])
            return
        names.add_options([Option(name, id=name) for name in sorted(result.charts)])
        chart_names = sorted(result.charts)
        names.highlighted = chart_names.index(previous) if previous in chart_names else 0
        self._show_custom_chart(chart_names[names.highlighted])

    @on(OptionList.OptionHighlighted, "#chart-names")
    def _chart_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self._show_custom_chart(event.option.id)

    def _show_custom_chart(self, name: str) -> None:
        chart = self._result.charts.get(name) if self._result is not None else None
        if chart is None:
            return
        series: List[Series] = [s for s in chart.series.values() if s.points]
        self.query_one("#chart", TimeSeriesChart).set_lines(
            [Line(s.name, s.points, SERIES_COLORS[i % len(SERIES_COLORS)], s.unit) for i, s in enumerate(series)])
