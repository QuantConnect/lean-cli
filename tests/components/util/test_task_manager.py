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

from unittest import mock

import pytest

from lean.components.util.task_manager import TaskManager


@mock.patch("time.sleep")
def test_poll_calls_make_request_until_is_done_returns_true(sleep) -> None:
    index = 0
    is_done_calls = []

    def make_request() -> int:
        nonlocal index
        index += 1
        return index

    def is_done(value: int) -> bool:
        is_done_calls.append(value)
        return value == 5

    task_manager = TaskManager(mock.Mock())
    task_manager.poll(make_request, is_done)

    assert is_done_calls == [1, 2, 3, 4, 5]


@mock.patch("time.sleep")
def test_poll_returns_last_data_from_make_request(sleep) -> None:
    index = 0

    def make_request() -> int:
        nonlocal index
        index += 1
        return index

    def is_done(value: int) -> bool:
        return value == 5

    task_manager = TaskManager(mock.Mock())
    result = task_manager.poll(make_request, is_done)

    assert result == 5


@mock.patch("time.sleep")
def test_poll_repeatedly_updates_progress_bar_when_get_progress_defined(sleep) -> None:
    index = 0

    def make_request() -> int:
        nonlocal index
        index += 1
        return index

    def is_done(value: int) -> bool:
        return value == 5

    def get_progress(value: int) -> float:
        return float(value) / 5.0

    logger = mock.Mock()
    progress_bar = mock.Mock()
    progress_bar.n = 0.0
    logger.progress.return_value = progress_bar

    task_manager = TaskManager(logger)
    task_manager.poll(make_request, is_done, get_progress=get_progress)

    assert progress_bar.update.mock_calls == [mock.call(0.2),
                                              mock.call(0.4),
                                              mock.call(0.6),
                                              mock.call(0.8),
                                              mock.call(1.0)]

    progress_bar.close.assert_called_once()


@mock.patch("time.sleep")
def test_poll_raises_when_make_request_raises(sleep) -> None:
    index = 0

    def make_request() -> int:
        nonlocal index
        index += 1

        if index == 3:
            raise RuntimeError(str(index))

        return index

    def is_done(value: int) -> bool:
        return value == 5

    def get_progress(value: int) -> float:
        return float(value) / 5.0

    logger = mock.Mock()
    progress_bar = mock.Mock()
    progress_bar.n = 0.0
    logger.progress.return_value = progress_bar

    task_manager = TaskManager(logger)

    with pytest.raises(RuntimeError) as err:
        task_manager.poll(make_request, is_done, get_progress=get_progress)

    assert str(err.value) == "3"
    progress_bar.close.assert_called_once()


@mock.patch("time.sleep")
def test_poll_closes_progress_bar_when_keyboard_interrupt_fired(sleep) -> None:
    index = 0

    def make_request() -> int:
        nonlocal index
        index += 1

        if index == 3:
            raise KeyboardInterrupt()

        return index

    def is_done(value: int) -> bool:
        return value == 5

    def get_progress(value: int) -> float:
        return float(value) / 5.0

    logger = mock.Mock()
    progress_bar = mock.Mock()
    progress_bar.n = 0.0
    logger.progress.return_value = progress_bar

    task_manager = TaskManager(logger)

    with pytest.raises(KeyboardInterrupt):
        task_manager.poll(make_request, is_done, get_progress=get_progress)

    progress_bar.close.assert_called_once()
