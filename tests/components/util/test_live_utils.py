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
from pathlib import Path
from typing import Any, Dict
from unittest import mock

import pytest

from lean.components.util.live_utils import _get_last_portfolio
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory

LOCAL_STATE = {"Cash": {"USD": {"Symbol": "USD", "Amount": 100000.0}}}
CLOUD_STATE = {"cash": {"USD": {"Symbol": "USD", "Amount": 5000.0}}}


def _live_directory() -> Path:
    return Path.cwd() / "Python Project" / "live"


def _create_deployment(directory: Path, state: Dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "config").write_text(json.dumps({"id": 3875119070}), encoding="utf-8")
    (directory / "L-3875119070.json").write_text(json.dumps(state), encoding="utf-8")


def _get_last_local_portfolio() -> Any:
    return _get_last_portfolio(mock.MagicMock(), None, Path.cwd() / "Python Project")


def test_get_last_portfolio_reads_the_latest_local_deployment() -> None:
    create_fake_lean_cli_directory()
    _create_deployment(_live_directory() / "2024-09-26_17-25-28", LOCAL_STATE)

    assert _get_last_local_portfolio() == {"cash": LOCAL_STATE["Cash"]}


@pytest.mark.parametrize("stray_entry,is_directory", [(".DS_Store", False), ("my-run", True)])
def test_get_last_portfolio_ignores_entries_that_are_not_deployments(stray_entry: str, is_directory: bool) -> None:
    create_fake_lean_cli_directory()
    _create_deployment(_live_directory() / "2024-09-26_17-25-28", LOCAL_STATE)
    if is_directory:
        (_live_directory() / stray_entry).mkdir()
    else:
        (_live_directory() / stray_entry).touch()

    with mock.patch.object(container.logger, "debug") as debug:
        assert _get_last_local_portfolio() == {"cash": LOCAL_STATE["Cash"]}

    assert any(stray_entry in str(call) for call in debug.call_args_list)


def test_get_last_portfolio_survives_a_deployment_name_before_1970() -> None:
    create_fake_lean_cli_directory()
    _create_deployment(_live_directory() / "2024-09-26_17-25-28", LOCAL_STATE)
    # converting this name to UTC raises OSError on Windows; elsewhere it is just an older deployment
    (_live_directory() / "1960-01-01_00-00-00").mkdir()

    assert _get_last_local_portfolio() == {"cash": LOCAL_STATE["Cash"]}


def test_get_last_portfolio_returns_none_without_deployments() -> None:
    create_fake_lean_cli_directory()
    _live_directory().mkdir()
    (_live_directory() / ".DS_Store").touch()

    assert _get_last_local_portfolio() is None


def test_get_last_portfolio_reads_a_deployment_in_a_custom_output_directory() -> None:
    create_fake_lean_cli_directory()
    _create_deployment(_live_directory() / "my-run", LOCAL_STATE)

    assert _get_last_local_portfolio() == {"cash": LOCAL_STATE["Cash"]}


def test_get_last_portfolio_prefers_the_cloud_deployment_when_it_is_more_recent() -> None:
    create_fake_lean_cli_directory()
    _create_deployment(_live_directory() / "2024-09-26_17-25-28", LOCAL_STATE)

    api_client = mock.MagicMock()
    api_client.get.side_effect = lambda endpoint, *args, **kwargs: {
        "live/read": {"success": True, "status": "Stopped", "stopped": "2030-01-01 00:00:00", "launched": "2029-12-31 00:00:00"},
        "live/portfolio/read": {"portfolio": CLOUD_STATE}
    }[endpoint]

    assert _get_last_portfolio(api_client, 1234, Path.cwd() / "Python Project") == CLOUD_STATE
