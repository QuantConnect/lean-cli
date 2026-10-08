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
from typing import Any, Dict, List, Optional
from unittest import mock

import pytest

from lean.container import container
from lean.ui.results import (CloudBacktest, LocalBacktest, list_cloud_backtests, list_local_backtests,
                             parse_cloud_backtest, parse_local_result, sort_newest_first)

# 2013-10-07 04:00 UTC to 2013-10-11 20:00 UTC, like the sample data backtests
START = 1381118400
END = 1381521600

BACKTEST_ID = "c9c84362d35b5ab2e8bd457446b74d58"


def create_equity_chart(points: int = 5) -> Dict[str, Any]:
    """Returns a Strategy Equity chart, whose equity series holds candles."""
    step = (END - START) / max(1, points - 1)
    return {"name": "Strategy Equity", "chartType": 0, "series": {
        "Equity": {"name": "Equity", "unit": "$", "index": 0, "seriesType": 2,
                   "values": [[START + i * step, 100000 + i, 100000 + i + 5, 100000 + i - 5, 100000 + i * 10]
                              for i in range(points)]},
        "Return": {"name": "Return", "unit": "%", "index": 1, "seriesType": 3, "values": [[START, 0.0]]},
    }}


def create_orders() -> Dict[str, Any]:
    return {
        "2": {"type": 0, "id": 2, "symbol": {"value": "SPY", "id": "SPY R735QTJ8XC9X", "permtick": "SPY"},
              "price": 145.34, "time": "2013-10-07T14:46:00Z", "quantity": -686.0, "status": 3,
              "tag": "Liquidated", "direction": 1, "value": -99705.8},
        "1": {"type": 0, "id": 1, "symbol": {"value": "SPY", "id": "SPY R735QTJ8XC9X", "permtick": "SPY"},
              "price": 145.33, "time": "2013-10-07T14:10:00Z", "quantity": 686.0, "status": 3,
              "tag": "", "direction": 0, "value": 99693.94},
    }


def create_result(status: str = "Completed", equity_points: int = 5) -> Dict[str, Any]:
    """Returns local backtest results in the format LEAN writes them, trimmed to a few points.

    LEAN only adds the algorithm configuration once the backtest has finished.
    """
    result = {
        "charts": {"Strategy Equity": create_equity_chart(equity_points)},
        "orders": create_orders(),
        "statistics": {"Total Orders": "2", "Net Profit": "-0.160%", "Sharpe Ratio": "1.028"},
        "runtimeStatistics": {"Equity": "$99,839.57", "Net Profit": "$-294.86", "Return": "-0.16 %"},
        "state": {"Status": status, "RuntimeError": ""},
    }
    if status != "Running":
        result["algorithmConfiguration"] = {"startDate": "2013-10-07T00:00:00Z", "endDate": "2013-10-11T23:59:59Z",
                                            "parameters": {"delay-ms": "30"}}
    return result


def create_local_backtest(project_dir: Path, name: str, result: Optional[Dict[str, Any]],
                          backtest_id: int = 1121419604) -> Path:
    """Writes a backtest output directory the way `lean backtest` leaves it."""
    output_dir = project_dir / "backtests" / name
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config").write_text(json.dumps({"id": backtest_id, "container": "lean_cli_abc"}))
    if result is not None:
        (output_dir / f"{backtest_id}.json").write_text(json.dumps(result))
    (output_dir / f"{backtest_id}-order-events.json").write_text("[]")
    (output_dir / "log.txt").write_text(
        "2026-10-08T20:01:00Z TRACE:: Engine.Run(): start\n"
        "2026-10-08T20:01:01Z TRACE:: AlgorithmManager.Run(): Begin DataStream - Start: 10/7/2013 12:00:00 AM "
        "Stop: 10/11/2013 11:59:59 PM Time: 10/4/2013 3:30:00 PM Warmup: True\n")
    return output_dir


def create_cloud_backtest(status: str = "Completed.", completed: bool = True, progress: float = 1.0) -> Dict[str, Any]:
    """Returns a backtest as the backtests/read endpoint returns it, without chart data."""
    return {"backtestId": BACKTEST_ID, "name": "Logical Red Monkey", "status": status, "completed": completed,
            "progress": progress, "created": "2026-10-08 19:45:10", "error": None,
            "backtestStart": "2013-10-07 00:00:00", "backtestEnd": "2013-10-11 23:59:59",
            "charts": {"Strategy Equity": {"name": "Strategy Equity", "series": {}}},
            "statistics": {"Net Profit": "136.589%"}, "runtimeStatistics": {"Equity": "$236,588.97"},
            "parameterSet": {"roc_window": "150"}}


def create_cloud_orders(count: int, first_id: int = 1) -> List[Dict[str, Any]]:
    return [dict(create_orders()["1"], id=first_id + i) for i in range(count)]


def mock_cloud_api(backtest: Dict[str, Any], orders: int = 0, logs: int = 0,
                   order_list: Optional[List[Dict[str, Any]]] = None) -> mock.Mock:
    """Makes the API client answer the backtest endpoints, paging orders and logs like the API.

    Pass order_list to change the orders the API returns while a test runs.
    """
    order_list = order_list if order_list is not None else create_cloud_orders(orders)
    log_lines = [f"line {i}" for i in range(logs)]

    def post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if endpoint == "backtests/read":
            return {"backtest": backtest}
        if endpoint == "backtests/chart/read":
            assert payload["name"] == "Strategy Equity"
            return {"chart": create_equity_chart()}
        if endpoint == "backtests/orders/read":
            assert payload["end"] - payload["start"] <= 100
            return {"orders": order_list[payload["start"]:payload["end"]], "length": len(order_list)}
        if endpoint == "backtests/read/log":
            assert payload["end"] - payload["start"] <= 200
            return {"logs": log_lines[payload["start"]:payload["end"]], "length": len(log_lines)}
        if endpoint == "backtests/list":
            return {"backtests": [{"backtestId": "a" * 32, "name": "Older", "created": "2026-01-01 10:00:00"},
                                  {"backtestId": "b" * 32, "name": "Newer", "created": "2026-10-08 19:45:10"}]}
        raise AssertionError(f"Unexpected endpoint {endpoint}")

    container.api_client.post = mock.Mock(side_effect=post)
    return container.api_client.post


def test_parse_local_result_reads_equity_closes() -> None:
    result = parse_local_result(create_result())

    assert result.equity[0] == (START, 100000)
    assert result.equity[-1] == (END, 100040)


def test_parse_local_result_skips_empty_points_and_reads_xy_points() -> None:
    data = create_result()
    data["charts"]["Strategy Equity"]["series"]["Equity"]["values"] = [[START, 1.0], [START + 60, None],
                                                                       {"x": END, "y": 2.0}]

    assert parse_local_result(data).equity == [(START, 1.0), (END, 2.0)]


def test_parse_local_result_reads_orders_sorted_by_id_with_readable_enums() -> None:
    orders = parse_local_result(create_result()).orders

    assert [o.id for o in orders] == [1, 2]
    assert (orders[0].type, orders[0].direction, orders[0].status) == ("Market", "Buy", "Filled")
    assert orders[1].direction == "Sell"
    assert orders[1].tag == "Liquidated"
    assert orders[0].time == datetime(2013, 10, 7, 14, 10, tzinfo=timezone.utc)


def test_parse_local_result_reads_statistics_status_and_configuration() -> None:
    result = parse_local_result(create_result())

    assert result.statistics["Sharpe Ratio"] == "1.028"
    assert result.runtime_statistics["Equity"] == "$99,839.57"
    assert (result.status, result.finished, result.progress) == ("Completed", True, 1.0)
    assert result.parameters == {"delay-ms": "30"}
    assert result.start == datetime(2013, 10, 7, tzinfo=timezone.utc)


def test_parse_local_result_of_a_running_backtest() -> None:
    result = parse_local_result(create_result(status="Running"))

    assert (result.status, result.finished) == ("Running", False)
    assert result.start is None


def test_local_backtest_progress_uses_the_date_range_from_the_log_while_running() -> None:
    data = create_result(status="Running", equity_points=5)
    data["charts"]["Strategy Equity"]["series"]["Equity"]["values"] = \
        data["charts"]["Strategy Equity"]["series"]["Equity"]["values"][:3]
    output_dir = create_local_backtest(Path.cwd() / "Project", "2026-10-08_16-00-57", data)

    result = LocalBacktest(output_dir).load()

    assert result.start == datetime(2013, 10, 7, tzinfo=timezone.utc)
    assert 0.45 < result.progress < 0.55


def test_local_backtest_finds_its_result_file_from_its_config() -> None:
    output_dir = create_local_backtest(Path.cwd() / "Project", "2026-10-08_16-00-57", create_result())
    (output_dir / "9999-summary.json").write_text("{}")

    backtest = LocalBacktest(output_dir)

    assert backtest.result_file == output_dir / "1121419604.json"
    assert backtest.load().name == "2026-10-08_16-00-57"
    assert backtest.load_orders(0, 100) == (backtest.load().orders, 2)
    assert [o.id for o in backtest.load_orders(1, 100)[0]] == [2]
    assert backtest.created == datetime(2026, 10, 8, 16, 0, 57).astimezone(timezone.utc)


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
    assert LocalBacktest(Path.cwd() / "Project" / "backtests" / "missing").load() is None


def test_local_backtest_reads_its_log() -> None:
    output_dir = create_local_backtest(Path.cwd() / "Project", "2026-10-08_16-00-57", create_result())

    assert LocalBacktest(output_dir).load_log()[0] == "2026-10-08T20:01:00Z TRACE:: Engine.Run(): start"


def test_list_local_backtests_returns_newest_first() -> None:
    project_dir = Path.cwd() / "Project"
    for name in ["2026-10-08_16-00-57", "2026-10-09_09-30-00", "2026-01-01_00-00-00"]:
        create_local_backtest(project_dir, name, create_result())

    names = [b.name for b in list_local_backtests(project_dir)]

    assert names == ["2026-10-09_09-30-00", "2026-10-08_16-00-57", "2026-01-01_00-00-00"]
    assert list_local_backtests(Path.cwd() / "Missing") == []
    assert list_local_backtests(None) == []


def test_parse_cloud_backtest() -> None:
    result = parse_cloud_backtest(create_cloud_backtest(), {"Strategy Equity": create_equity_chart()})

    assert result.name == "Logical Red Monkey"
    assert (result.status, result.finished, result.progress) == ("Completed", True, 1.0)
    assert result.statistics == {"Net Profit": "136.589%"}
    assert result.parameters == {"roc_window": "150"}
    assert result.equity[-1] == (END, 100040)
    assert result.start == datetime(2013, 10, 7, tzinfo=timezone.utc)


def test_parse_cloud_backtest_while_running_uses_reported_progress() -> None:
    backtest = create_cloud_backtest(status="Running", completed=False, progress=0.42)
    backtest["statistics"] = []

    result = parse_cloud_backtest(backtest, {})

    assert (result.finished, result.progress) == (False, 0.42)
    assert result.statistics == {}
    assert result.equity == []


def test_cloud_backtest_loads_the_backtest_and_only_its_equity_chart() -> None:
    post = mock_cloud_api(create_cloud_backtest())

    result = CloudBacktest(123, BACKTEST_ID).load()

    assert result.equity[-1] == (END, 100040)
    chart_requests = [c for c in post.call_args_list if c.args[0] == "backtests/chart/read"]
    assert len(chart_requests) == 1
    assert chart_requests[0].args[1]["start"] == int(datetime(2013, 10, 7, tzinfo=timezone.utc).timestamp())


def test_cloud_backtest_without_a_chart_yet_loads_the_summary() -> None:
    backtest = create_cloud_backtest(status="In Queue...", completed=False, progress=0)
    backtest["charts"] = {}
    post = mock_cloud_api(backtest)

    result = CloudBacktest(123, BACKTEST_ID).load()

    assert result.status == "In Queue"
    assert result.equity == []
    assert all(c.args[0] != "backtests/chart/read" for c in post.call_args_list)


def test_cloud_backtest_loads_one_page_of_orders_with_the_total() -> None:
    post = mock_cloud_api(create_cloud_backtest(), orders=250)

    orders, total = CloudBacktest(123, BACKTEST_ID).load_orders(100, 200)

    assert [o.id for o in orders] == list(range(101, 201))
    assert total == 250
    assert post.call_count == 1


def test_cloud_backtest_never_asks_for_more_than_a_page_of_orders() -> None:
    post = mock_cloud_api(create_cloud_backtest(), orders=250)

    orders, _ = CloudBacktest(123, BACKTEST_ID).load_orders(0, 1000)

    assert len(orders) == 100
    assert post.call_args.args[1]["end"] == 100


def test_cloud_backtest_reads_the_last_log_lines() -> None:
    mock_cloud_api(create_cloud_backtest(), logs=2500)

    lines = CloudBacktest(123, BACKTEST_ID).load_log()

    assert len(lines) == 2000
    assert (lines[0], lines[-1]) == ("line 500", "line 2499")


def test_list_cloud_backtests_returns_newest_first() -> None:
    mock_cloud_api(create_cloud_backtest())

    backtests = list_cloud_backtests(123)

    assert [b.name for b in backtests] == ["Newer", "Older"]
    assert backtests[0].created == datetime(2026, 10, 8, 19, 45, 10, tzinfo=timezone.utc)


def test_sort_newest_first_mixes_local_and_cloud_backtests() -> None:
    local = LocalBacktest(Path("backtests") / "2026-05-01_12-00-00")
    cloud: List = [CloudBacktest(1, "a" * 32, "Old", datetime(2025, 1, 1, tzinfo=timezone.utc)),
                   CloudBacktest(1, "b" * 32, "New", datetime(2026, 10, 1, tzinfo=timezone.utc))]

    assert [b.name for b in sort_newest_first([local] + cloud)] == ["New", "2026-05-01_12-00-00", "Old"]


def test_cloud_backtest_waits_while_the_api_prepares_the_orders() -> None:
    post = mock_cloud_api(create_cloud_backtest(), orders=3)
    serve = post.side_effect
    answers = iter([{"status": "loading", "progress": 0.0, "success": True}] * 2)
    post.side_effect = lambda endpoint, payload: next(answers, None) or serve(endpoint, payload)

    with mock.patch("lean.ui.results.CLOUD_LOADING_DELAY_SECONDS", 0):
        orders, total = CloudBacktest(123, BACKTEST_ID).load_orders(0, 100)

    assert (len(orders), total) == (3, 3)
    assert post.call_count == 3


def test_cloud_backtest_gives_up_when_the_api_keeps_loading() -> None:
    container.api_client.post = mock.Mock(return_value={"status": "loading", "progress": 0.5, "success": True})

    with mock.patch("lean.ui.results.CLOUD_LOADING_DELAY_SECONDS", 0), \
            pytest.raises(RuntimeError, match="still preparing"):
        CloudBacktest(123, BACKTEST_ID).load_orders(0, 100)

    assert container.api_client.post.call_count == 30
