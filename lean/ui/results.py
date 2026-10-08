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

# Reads LEAN backtest results. Local result files and the cloud API share the same JSON format for charts,
# statistics and orders, so both are parsed here.

from dataclasses import dataclass, field
from datetime import datetime, timezone
from json import loads
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# LEAN enums, see Common/Orders/OrderTypes.cs and Common/Orders/OrderEnums.cs
ORDER_TYPES = ["Market", "Limit", "Stop Market", "Stop Limit", "Market On Open", "Market On Close",
               "Option Exercise", "Limit If Touched", "Combo Market", "Combo Limit", "Combo Leg Limit",
               "Trailing Stop"]
ORDER_STATUSES = {0: "New", 1: "Submitted", 2: "Partially Filled", 3: "Filled", 5: "Canceled", 6: "None",
                  7: "Invalid", 8: "Cancel Pending", 9: "Update Submitted"}
ORDER_DIRECTIONS = ["Buy", "Sell", "Hold"]

# The candle series type, whose points are [time, open, high, low, close], see Common/SeriesType.cs
CANDLE_SERIES_TYPE = 2

# Files written next to the result file that are not the result itself
_NON_RESULT_SUFFIXES = ("-order-events.json", "-summary.json")


@dataclass
class Series:
    name: str
    unit: str
    series_type: int
    points: List[Tuple[float, float]]
    """(unix time, value) pairs; candle series are reduced to their closing value."""


@dataclass
class Chart:
    name: str
    series: Dict[str, Series]


@dataclass
class Order:
    id: int
    time: Optional[datetime]
    symbol: str
    type: str
    direction: str
    quantity: float
    price: float
    value: float
    status: str
    tag: str


@dataclass
class BacktestResult:
    charts: Dict[str, Chart] = field(default_factory=dict)
    statistics: Dict[str, str] = field(default_factory=dict)
    runtime_statistics: Dict[str, str] = field(default_factory=dict)
    orders: List[Order] = field(default_factory=list)
    status: str = ""
    runtime_error: str = ""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    parameters: Dict[str, str] = field(default_factory=dict)

    def series(self, chart: str, series: str) -> Optional[Series]:
        found = self.charts.get(chart)
        return found.series.get(series) if found is not None else None

    @property
    def equity(self) -> Optional[Series]:
        return self.series("Strategy Equity", "Equity")

    @property
    def drawdown(self) -> Optional[Series]:
        return self.series("Drawdown", "Equity Drawdown")

    @property
    def benchmark(self) -> Optional[Series]:
        return self.series("Benchmark", "Benchmark")

    @property
    def progress(self) -> Optional[float]:
        """How far the backtest got through its date range, between 0 and 1, based on the last equity point."""
        equity = self.equity
        if self.status == "Completed":
            return 1.0
        if equity is None or not equity.points or self.start is None or self.end is None:
            return None
        total = (self.end - self.start).total_seconds()
        done = equity.points[-1][0] - self.start.timestamp()
        return min(max(done / total, 0.0), 1.0) if total > 0 else None


def _parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_point(value: Any) -> Optional[Tuple[float, float]]:
    """Parses a chart point, which is [time, value], [time, open, high, low, close] or {"x": time, "y": value}."""
    if isinstance(value, dict):
        time, number = value.get("x"), value.get("y")
    elif isinstance(value, list) and len(value) >= 2:
        time, number = value[0], value[-1]
    else:
        return None
    if time is None or number is None:
        return None
    return float(time), float(number)


def _parse_series(data: Dict[str, Any]) -> Series:
    points = [p for p in (_parse_point(v) for v in data.get("values") or []) if p is not None]
    return Series(name=data.get("name", ""),
                  unit=data.get("unit", ""),
                  series_type=data.get("seriesType", 0),
                  points=points)


def _parse_order(data: Dict[str, Any]) -> Order:
    symbol = data.get("symbol") or {}
    order_type = data.get("type", 0)
    direction = data.get("direction", 0)
    return Order(id=data.get("id", 0),
                 time=_parse_time(data.get("time")),
                 symbol=symbol.get("value", "") if isinstance(symbol, dict) else str(symbol),
                 type=ORDER_TYPES[order_type] if 0 <= order_type < len(ORDER_TYPES) else str(order_type),
                 direction=ORDER_DIRECTIONS[direction] if 0 <= direction < len(ORDER_DIRECTIONS) else str(direction),
                 quantity=data.get("quantity", 0.0),
                 price=data.get("price", 0.0),
                 value=data.get("value", 0.0),
                 status=ORDER_STATUSES.get(data.get("status"), str(data.get("status"))),
                 tag=data.get("tag") or "")


def parse_backtest_result(data: Dict[str, Any]) -> BacktestResult:
    """Parses LEAN backtest results, as stored in the result file of a local backtest."""
    charts = {}
    for name, chart in (data.get("charts") or {}).items():
        charts[name] = Chart(name=name,
                             series={n: _parse_series(s) for n, s in (chart.get("series") or {}).items()})

    orders = data.get("orders") or {}
    if isinstance(orders, dict):
        orders = list(orders.values())

    state = data.get("state") or {}
    configuration = data.get("algorithmConfiguration") or {}

    return BacktestResult(charts=charts,
                          statistics=data.get("statistics") or {},
                          runtime_statistics=data.get("runtimeStatistics") or {},
                          orders=sorted((_parse_order(o) for o in orders), key=lambda o: o.id),
                          status=state.get("Status", ""),
                          runtime_error=state.get("RuntimeError", ""),
                          start=_parse_time(configuration.get("startDate")),
                          end=_parse_time(configuration.get("endDate")),
                          parameters=configuration.get("parameters") or {})


@dataclass
class LocalBacktest:
    """A backtest stored in a project's backtests directory."""

    path: Path

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def result_file(self) -> Optional[Path]:
        """The result file, which LEAN names after the backtest id and rewrites while the backtest runs."""
        config_file = self.path / "config"
        if config_file.is_file():
            try:
                result_file = self.path / f"{loads(config_file.read_text(encoding='utf-8'))['id']}.json"
                if result_file.is_file():
                    return result_file
            except (ValueError, KeyError):
                pass

        candidates = [f for f in self.path.glob("*.json")
                      if f.stem.lstrip("L-").isdigit() and not f.name.endswith(_NON_RESULT_SUFFIXES)]
        return max(candidates, key=lambda f: f.stat().st_mtime) if candidates else None

    @property
    def log_file(self) -> Path:
        return self.path / "log.txt"

    def load(self) -> Optional[BacktestResult]:
        """Reads the result file, returns None if there is none yet or it is being written."""
        result_file = self.result_file
        if result_file is None:
            return None
        try:
            return parse_backtest_result(loads(result_file.read_text(encoding="utf-8")))
        except ValueError:
            return None


def list_local_backtests(project_dir: Path) -> List[LocalBacktest]:
    """Returns the backtests of a project, newest first."""
    backtests_dir = project_dir / "backtests"
    if not backtests_dir.is_dir():
        return []
    return sorted((LocalBacktest(d) for d in backtests_dir.iterdir() if d.is_dir()),
                  key=lambda b: b.name, reverse=True)
