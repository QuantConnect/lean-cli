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

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from lean.ui.results import LocalBacktest, list_local_backtests, parse_backtest_result

# 2013-10-07 04:00 UTC to 2013-10-11 20:00 UTC, like the sample data backtests
START = 1381118400
END = 1381521600


def create_result(status: str = "Completed", equity_points: int = 5) -> Dict[str, Any]:
    """Returns backtest results in the format LEAN writes them, trimmed to a few points."""
    step = (END - START) / max(1, equity_points - 1)
    equity = [[START + i * step, 100000 + i, 100000 + i + 5, 100000 + i - 5, 100000 + i * 10]
              for i in range(equity_points)]

    return {
        "charts": {
            "Strategy Equity": {"name": "Strategy Equity", "chartType": 0, "series": {
                "Equity": {"name": "Equity", "unit": "$", "index": 0, "seriesType": 2, "values": equity},
                "Return": {"name": "Return", "unit": "%", "index": 1, "seriesType": 3,
                           "values": [[START, 0.0], [END, 0.4]]},
            }},
            "Drawdown": {"name": "Drawdown", "chartType": 0, "series": {
                "Equity Drawdown": {"name": "Equity Drawdown", "unit": "%", "seriesType": 0,
                                    "values": [[START, 0.0], [END, -0.34]]},
            }},
            "Benchmark": {"name": "Benchmark", "chartType": 0, "series": {
                "Benchmark": {"name": "Benchmark", "unit": "$", "seriesType": 0,
                              "values": [[START, 146.0], [END, 147.0]]},
            }},
            "Indicators": {"name": "Indicators", "chartType": 0, "series": {
                "Fast EMA": {"name": "Fast EMA", "unit": "$", "seriesType": 0,
                             "values": [[START, 145.0], [START + 60, None], {"x": END, "y": 146.0}]},
            }},
        },
        "orders": {
            "2": {"type": 0, "id": 2, "symbol": {"value": "SPY", "id": "SPY R735QTJ8XC9X", "permtick": "SPY"},
                  "price": 145.34, "time": "2013-10-07T14:46:00Z", "quantity": -686.0, "status": 3,
                  "tag": "Liquidated", "direction": 1, "value": -99705.8},
            "1": {"type": 0, "id": 1, "symbol": {"value": "SPY", "id": "SPY R735QTJ8XC9X", "permtick": "SPY"},
                  "price": 145.33, "time": "2013-10-07T14:10:00Z", "quantity": 686.0, "status": 3,
                  "tag": "", "direction": 0, "value": 99693.94},
        },
        "statistics": {"Total Orders": "2", "Net Profit": "-0.160%", "Sharpe Ratio": "1.028"},
        "runtimeStatistics": {"Equity": "$99,839.57", "Net Profit": "$-294.86", "Return": "-0.16 %"},
        "state": {"Status": status, "RuntimeError": ""},
        "algorithmConfiguration": {"startDate": "2013-10-07T00:00:00Z", "endDate": "2013-10-11T23:59:59Z",
                                   "parameters": {"delay-ms": "30"}},
    }


def create_local_backtest(project_dir: Path, name: str, result: Dict[str, Any], backtest_id: int = 1121419604) -> Path:
    """Writes a backtest output directory the way `lean backtest` leaves it."""
    output_dir = project_dir / "backtests" / name
    output_dir.mkdir(parents=True)
    (output_dir / "config").write_text(json.dumps({"id": backtest_id, "container": "lean_cli_abc"}))
    (output_dir / f"{backtest_id}.json").write_text(json.dumps(result))
    (output_dir / f"{backtest_id}-order-events.json").write_text("[]")
    (output_dir / "log.txt").write_text("2026-10-08T20:01:00Z TRACE:: Engine.Run(): start\n")
    return output_dir


def test_parse_backtest_result_reads_charts_and_reduces_candles_to_closes() -> None:
    result = parse_backtest_result(create_result())

    assert result.equity.unit == "$"
    assert result.equity.points[0] == (START, 100000)
    assert result.equity.points[-1] == (END, 100040)
    assert result.drawdown.points == [(START, 0.0), (END, -0.34)]
    assert result.benchmark.points[0] == (START, 146.0)


def test_parse_backtest_result_skips_empty_points_and_reads_xy_points() -> None:
    result = parse_backtest_result(create_result())

    assert result.series("Indicators", "Fast EMA").points == [(START, 145.0), (END, 146.0)]


def test_parse_backtest_result_reads_orders_sorted_by_id_with_readable_enums() -> None:
    orders = parse_backtest_result(create_result()).orders

    assert [o.id for o in orders] == [1, 2]
    assert (orders[0].type, orders[0].direction, orders[0].status) == ("Market", "Buy", "Filled")
    assert orders[1].direction == "Sell"
    assert orders[1].tag == "Liquidated"
    assert orders[0].time == datetime(2013, 10, 7, 14, 10, tzinfo=timezone.utc)


def test_parse_backtest_result_reads_statistics_state_and_configuration() -> None:
    result = parse_backtest_result(create_result())

    assert result.statistics["Sharpe Ratio"] == "1.028"
    assert result.runtime_statistics["Equity"] == "$99,839.57"
    assert result.status == "Completed"
    assert result.parameters == {"delay-ms": "30"}
    assert result.start == datetime(2013, 10, 7, tzinfo=timezone.utc)


def test_parse_backtest_result_reads_cloud_backtests_with_list_orders() -> None:
    data = create_result()
    data["orders"] = list(data["orders"].values())
    del data["state"]

    result = parse_backtest_result(data)

    assert [o.id for o in result.orders] == [1, 2]
    assert result.status == ""


def test_progress_of_a_running_backtest_comes_from_its_last_equity_point() -> None:
    data = create_result(status="Running", equity_points=5)
    data["charts"]["Strategy Equity"]["series"]["Equity"]["values"] = \
        data["charts"]["Strategy Equity"]["series"]["Equity"]["values"][:3]

    progress = parse_backtest_result(data).progress

    assert 0.45 < progress < 0.55


def test_progress_of_a_completed_backtest_is_one() -> None:
    assert parse_backtest_result(create_result()).progress == 1.0


def test_local_backtest_finds_its_result_file_from_its_config() -> None:
    project_dir = Path.cwd() / "Project"
    output_dir = create_local_backtest(project_dir, "2026-10-08_16-00-57", create_result())
    (output_dir / "9999-summary.json").write_text("{}")

    backtest = LocalBacktest(output_dir)

    assert backtest.result_file == output_dir / "1121419604.json"
    assert backtest.load().statistics["Total Orders"] == "2"


def test_local_backtest_finds_its_result_file_without_a_config() -> None:
    output_dir = create_local_backtest(Path.cwd() / "Project", "2026-10-08_16-00-57", create_result())
    (output_dir / "config").unlink()

    assert LocalBacktest(output_dir).result_file == output_dir / "1121419604.json"


def test_local_backtest_without_results_or_with_a_partially_written_file_loads_nothing() -> None:
    output_dir = create_local_backtest(Path.cwd() / "Project", "2026-10-08_16-00-57", create_result())
    backtest = LocalBacktest(output_dir)

    (output_dir / "1121419604.json").write_text('{"charts": {"Strategy Eq')
    assert backtest.load() is None

    (output_dir / "1121419604.json").unlink()
    assert backtest.load() is None


def test_list_local_backtests_returns_newest_first() -> None:
    project_dir = Path.cwd() / "Project"
    for name in ["2026-10-08_16-00-57", "2026-10-09_09-30-00", "2026-01-01_00-00-00"]:
        create_local_backtest(project_dir, name, create_result())

    names = [b.name for b in list_local_backtests(project_dir)]

    assert names == ["2026-10-09_09-30-00", "2026-10-08_16-00-57", "2026-01-01_00-00-00"]
    assert list_local_backtests(Path.cwd() / "Missing") == []
