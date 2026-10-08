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

# Reads LEAN backtest results from local result files and from the cloud API, which share the same JSON format
# for charts, statistics and orders. Only the Strategy Equity chart is read.

from dataclasses import dataclass, field
from datetime import datetime, timezone
from json import loads
from re import compile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EQUITY_CHART = "Strategy Equity"
EQUITY_SERIES = "Equity"

# LEAN enums, see Common/Orders/OrderTypes.cs and Common/Orders/OrderEnums.cs
ORDER_TYPES = ["Market", "Limit", "Stop Market", "Stop Limit", "Market On Open", "Market On Close",
               "Option Exercise", "Limit If Touched", "Combo Market", "Combo Limit", "Combo Leg Limit",
               "Trailing Stop"]
ORDER_STATUSES = {0: "New", 1: "Submitted", 2: "Partially Filled", 3: "Filled", 5: "Canceled", 6: "None",
                  7: "Invalid", 8: "Cancel Pending", 9: "Update Submitted"}
ORDER_DIRECTIONS = ["Buy", "Sell", "Hold"]

# Algorithm statuses after which a backtest's results no longer change, see Common/AlgorithmStatus.cs
FINISHED_STATUSES = {"Completed", "RuntimeError", "Runtime Error", "Stopped", "Liquidated", "Deleted"}

# The cloud API returns at most this many orders and log lines per request
CLOUD_ORDERS_PAGE = 100
CLOUD_LOG_PAGE = 200
MAX_LOG_LINES = 2000

# Points to request of the equity chart from the cloud, which samples it down to this many
CLOUD_CHART_POINTS = 1000

# LEAN logs the date range when a backtest starts, before the result file has it
_DATA_STREAM_RANGE = compile(r"Begin DataStream - Start: (.+?) Stop: (.+?) Time:")
_LEAN_LOG_TIME_FORMAT = "%m/%d/%Y %I:%M:%S %p"

# Files written next to a local result file that are not the result itself
_NON_RESULT_SUFFIXES = ("-order-events.json", "-summary.json")


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
    name: str = ""
    equity: List[Tuple[float, float]] = field(default_factory=list)
    """(unix time, equity) points of the Strategy Equity chart, candles reduced to their closing value."""
    statistics: Dict[str, str] = field(default_factory=dict)
    runtime_statistics: Dict[str, str] = field(default_factory=dict)
    orders: Optional[List[Order]] = None
    """The orders, or None if they are loaded separately (see BacktestSource.load_orders)."""
    status: str = ""
    finished: bool = False
    runtime_error: str = ""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    parameters: Dict[str, str] = field(default_factory=dict)
    reported_progress: Optional[float] = None

    @property
    def progress(self) -> Optional[float]:
        """How far the backtest is, between 0 and 1.

        Cloud backtests report it, for local backtests it is how far the equity chart got through the date range.
        """
        if self.finished:
            return 1.0
        if self.reported_progress is not None:
            return self.reported_progress
        if not self.equity or self.start is None or self.end is None:
            return None
        total = (self.end - self.start).total_seconds()
        done = self.equity[-1][0] - self.start.timestamp()
        return min(max(done / total, 0.0), 1.0) if total > 0 else None


def _parse_time(value: Any) -> Optional[datetime]:
    """Parses a LEAN time, either unix seconds or an ISO 8601 string, which is UTC unless it says otherwise."""
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        time = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return time if time.tzinfo is not None else time.replace(tzinfo=timezone.utc)


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


def parse_equity(charts: Dict[str, Any]) -> List[Tuple[float, float]]:
    """Returns the points of the Equity series of the Strategy Equity chart."""
    series = ((charts.get(EQUITY_CHART) or {}).get("series") or {}).get(EQUITY_SERIES) or {}
    return [p for p in (_parse_point(v) for v in series.get("values") or []) if p is not None]


def parse_order(data: Dict[str, Any]) -> Order:
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


def parse_orders(orders: Any) -> List[Order]:
    """Parses orders, which local results store by id and the cloud API returns as a list."""
    if isinstance(orders, dict):
        orders = list(orders.values())
    return sorted((parse_order(o) for o in orders or []), key=lambda o: o.id)


def parse_local_result(data: Dict[str, Any]) -> BacktestResult:
    """Parses the result file LEAN writes while running a backtest locally."""
    state = data.get("state") or {}
    configuration = data.get("algorithmConfiguration") or {}
    status = state.get("Status", "")

    return BacktestResult(equity=parse_equity(data.get("charts") or {}),
                          statistics=data.get("statistics") or {},
                          runtime_statistics=data.get("runtimeStatistics") or {},
                          orders=parse_orders(data.get("orders")),
                          status=status or "Running",
                          finished=status in FINISHED_STATUSES,
                          runtime_error=state.get("RuntimeError", ""),
                          start=_parse_time(configuration.get("startDate")),
                          end=_parse_time(configuration.get("endDate")),
                          parameters=configuration.get("parameters") or {})


def parse_cloud_backtest(backtest: Dict[str, Any], charts: Dict[str, Any]) -> BacktestResult:
    """Parses a backtest from the backtests/read endpoint and its equity chart from backtests/chart/read."""
    statistics = backtest.get("statistics")
    parameters = backtest.get("parameterSet")
    return BacktestResult(name=backtest.get("name", ""),
                          equity=parse_equity(charts),
                          statistics=statistics if isinstance(statistics, dict) else {},
                          runtime_statistics=backtest.get("runtimeStatistics") or {},
                          status=(backtest.get("status") or "").rstrip("."),
                          finished=bool(backtest.get("completed")),
                          runtime_error=backtest.get("error") or "",
                          start=_parse_time(backtest.get("backtestStart")),
                          end=_parse_time(backtest.get("backtestEnd")),
                          parameters=parameters if isinstance(parameters, dict) else {},
                          reported_progress=backtest.get("progress"))


class BacktestSource:
    """A backtest whose results can be shown, stored locally or in the cloud."""

    location = ""
    poll_seconds = 15

    @property
    def id(self) -> str:
        raise NotImplementedError()

    @property
    def name(self) -> str:
        raise NotImplementedError()

    @property
    def created(self) -> Optional[datetime]:
        raise NotImplementedError()

    def load(self) -> Optional[BacktestResult]:
        """Loads the summary and equity chart, returns None if there are no results yet. Blocks."""
        raise NotImplementedError()

    def load_orders(self) -> List[Order]:
        raise NotImplementedError()

    def load_log(self) -> List[str]:
        raise NotImplementedError()


class LocalBacktest(BacktestSource):
    """A backtest stored in a project's backtests directory, whose result file LEAN rewrites while it runs."""

    location = "local"
    poll_seconds = 10

    def __init__(self, path: Path) -> None:
        self.path = path
        self._last_result: Optional[BacktestResult] = None

    @property
    def id(self) -> str:
        return str(self.path)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def created(self) -> Optional[datetime]:
        try:
            return datetime.strptime(self.path.name, "%Y-%m-%d_%H-%M-%S").astimezone(timezone.utc)
        except ValueError:
            return None

    @property
    def result_file(self) -> Optional[Path]:
        """The result file, which LEAN names after the backtest id."""
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

    def load(self) -> Optional[BacktestResult]:
        """Reads the result file, returns None if there is none yet or it is being written."""
        result_file = self.result_file
        if result_file is None:
            return None
        try:
            result = parse_local_result(loads(result_file.read_text(encoding="utf-8")))
        except ValueError:
            return None
        result.name = self.name
        if result.start is None or result.end is None:
            result.start, result.end = self._date_range_from_log()
        self._last_result = result
        return result

    def _date_range_from_log(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Reads the backtest's date range from its log, which has it from the start of the run."""
        log_file = self.path / "log.txt"
        if not log_file.is_file():
            return None, None
        with log_file.open(encoding="utf-8", errors="replace") as file:
            for line in file:
                match = _DATA_STREAM_RANGE.search(line)
                if match is not None:
                    try:
                        return tuple(datetime.strptime(m, _LEAN_LOG_TIME_FORMAT).replace(tzinfo=timezone.utc)
                                     for m in match.groups())
                    except ValueError:
                        break
        return None, None

    def load_orders(self) -> List[Order]:
        result = self._last_result or self.load()
        return result.orders or [] if result is not None else []

    def load_log(self) -> List[str]:
        log_file = self.path / "log.txt"
        if not log_file.is_file():
            return []
        return log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-MAX_LOG_LINES:]


class CloudBacktest(BacktestSource):
    """A backtest in the cloud, read through the API."""

    location = "cloud"
    poll_seconds = 15

    def __init__(self, project_id: int, backtest_id: str, name: str = "", created: Optional[datetime] = None) -> None:
        self.project_id = project_id
        self.backtest_id = backtest_id
        self._name = name
        self._created = created

    @property
    def id(self) -> str:
        return self.backtest_id

    @property
    def name(self) -> str:
        return self._name or self.backtest_id

    @property
    def created(self) -> Optional[datetime]:
        return self._created

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        from lean.container import container
        return container.api_client.post(endpoint, {"projectId": self.project_id, "backtestId": self.backtest_id,
                                                    **payload})

    def load(self) -> Optional[BacktestResult]:
        backtest = self._post("backtests/read", {})["backtest"]
        self._name = backtest.get("name") or self._name
        self._created = _parse_time(backtest.get("created")) or self._created

        charts = {}
        start, end = _parse_time(backtest.get("backtestStart")), _parse_time(backtest.get("backtestEnd"))
        if EQUITY_CHART in (backtest.get("charts") or {}) and start is not None and end is not None:
            try:
                chart = self._post("backtests/chart/read", {"name": EQUITY_CHART, "count": CLOUD_CHART_POINTS,
                                                            "start": int(start.timestamp()),
                                                            "end": int(end.timestamp())}).get("chart")
                if chart:
                    charts[EQUITY_CHART] = chart
            except Exception:
                # The chart is not available until the backtest has produced some results
                pass

        return parse_cloud_backtest(backtest, charts)

    def load_orders(self) -> List[Order]:
        orders: List[Dict[str, Any]] = []
        while True:
            page = self._post("backtests/orders/read", {"start": len(orders), "end": len(orders) + CLOUD_ORDERS_PAGE})
            orders.extend(page.get("orders") or [])
            if not page.get("orders") or len(orders) >= page.get("length", 0):
                return parse_orders(orders)

    def load_log(self) -> List[str]:
        first = self._post("backtests/read/log", {"start": 0, "end": CLOUD_LOG_PAGE, "query": " "})
        length = first.get("length", 0)
        start = max(0, length - MAX_LOG_LINES)
        lines: List[str] = list(first.get("logs") or []) if start == 0 else []
        position = len(lines) if start == 0 else start
        while position < length:
            page = self._post("backtests/read/log", {"start": position, "end": min(position + CLOUD_LOG_PAGE, length),
                                                     "query": " "})
            if not page.get("logs"):
                break
            lines.extend(page["logs"])
            position += len(page["logs"])
        return lines


class PendingCloudBacktest(BacktestSource):
    """A cloud backtest being pushed and compiled, which has no id or results yet."""

    location = "cloud"

    @property
    def id(self) -> str:
        return "pending"

    @property
    def name(self) -> str:
        return "New cloud backtest"

    @property
    def created(self) -> Optional[datetime]:
        return datetime.now(timezone.utc)

    def load(self) -> Optional[BacktestResult]:
        return None

    def load_orders(self) -> List[Order]:
        return []

    def load_log(self) -> List[str]:
        return []


def list_local_backtests(project_dir: Optional[Path]) -> List[LocalBacktest]:
    """Returns the backtests of a local project, newest first."""
    backtests_dir = project_dir / "backtests" if project_dir is not None else None
    if backtests_dir is None or not backtests_dir.is_dir():
        return []
    return sorted((LocalBacktest(d) for d in backtests_dir.iterdir() if d.is_dir()),
                  key=lambda b: b.name, reverse=True)


def list_cloud_backtests(project_id: int) -> List[CloudBacktest]:
    """Returns the backtests of a cloud project, newest first. Makes a blocking API request."""
    from lean.container import container

    data = container.api_client.post("backtests/list", {"projectId": project_id, "includeStatistics": False})
    backtests = [CloudBacktest(project_id, b["backtestId"], b.get("name", ""), _parse_time(b.get("created")))
                 for b in data.get("backtests") or []]
    return sorted(backtests, key=lambda b: b.created or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


def sort_newest_first(backtests: List[BacktestSource]) -> List[BacktestSource]:
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(backtests, key=lambda b: b.created or oldest, reverse=True)
