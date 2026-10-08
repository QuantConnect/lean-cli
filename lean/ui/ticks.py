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

# Chooses chart axis ticks at round values and round times, the way charting libraries do

from datetime import datetime, timezone
from math import ceil, floor, log10
from typing import List, Tuple

_MINUTE = 60
_HOUR = 60 * _MINUTE
_DAY = 24 * _HOUR

# (step, step is in months rather than seconds, label format)
_TIME_STEPS = [(s * _MINUTE, False, "%H:%M") for s in (1, 5, 15, 30)] + \
              [(s * _HOUR, False, "%m-%d %H:%M") for s in (1, 2, 4, 6, 12)] + \
              [(s * _DAY, False, "%Y-%m-%d") for s in (1, 2, 7, 14)] + \
              [(s, True, "%Y-%m") for s in (1, 2, 3, 6)] + \
              [(s * 12, True, "%Y") for s in (1, 2, 5, 10, 20, 50)]


def value_ticks(low: float, high: float, max_ticks: int) -> Tuple[List[float], float]:
    """Returns ticks at round values (1, 2, 2.5 or 5 times a power of ten) covering the range, and their step."""
    if high <= low:
        return [low], 0.0

    # Use the smallest round step that keeps the number of ticks within the limit
    magnitude = 10 ** floor(log10((high - low) / max(1, max_ticks)))
    for step in (m * magnitude * scale for scale in (1, 10, 100) for m in (1, 2, 2.5, 5)):
        first = ceil(low / step - 1e-9)
        last = floor(high / step + 1e-9)
        if 0 < last - first + 1 <= max_ticks:
            return [0.0 if i == 0 else i * step for i in range(first, last + 1)], step

    # The range is narrower than a round step, so label its ends instead
    return [low, high], high - low


def format_value_ticks(ticks: List[float], step: float, unit: str = "") -> List[str]:
    """Formats ticks compactly with the precision their step needs, like $1.25M or 12.5%."""
    largest = max(abs(t) for t in ticks)
    divisor, suffix = next(((d, s) for d, s in [(1e9, "B"), (1e6, "M"), (1e3, "k")] if largest >= d), (1, ""))
    # The fewest decimals that show the step exactly, so 0.25 steps get 2 decimals and 5 steps get none
    scaled_step = step / divisor
    decimals = next((d for d in range(7) if abs(round(scaled_step, d) - scaled_step) < scaled_step * 1e-6), 2) \
        if scaled_step > 0 else 2

    labels = []
    for tick in ticks:
        text = f"{abs(tick) / divisor:,.{decimals}f}{suffix}"
        sign = "-" if tick < 0 else ""
        labels.append(f"{sign}${text}" if unit == "$" else f"{sign}{text}%" if unit == "%" else f"{sign}{text}")
    return labels


def _add_months(time: datetime, months: int) -> datetime:
    month_index = time.year * 12 + time.month - 1 + months
    return time.replace(year=month_index // 12, month=month_index % 12 + 1)


def time_ticks(low: float, high: float, max_ticks: int) -> Tuple[List[float], List[str]]:
    """Returns ticks at round UTC times (whole hours, days, months, years) covering the range, and their labels."""
    if high <= low:
        return [low], [datetime.fromtimestamp(low, tz=timezone.utc).strftime("%Y-%m-%d")]

    for step, in_months, label_format in _TIME_STEPS:
        if in_months:
            start = datetime.fromtimestamp(low, tz=timezone.utc).replace(day=1, hour=0, minute=0, second=0,
                                                                         microsecond=0)
            start = _add_months(start, (-(start.year * 12 + start.month - 1)) % step)
            if start.timestamp() < low:
                start = _add_months(start, step)
            times = []
            while start.timestamp() <= high and len(times) <= max_ticks:
                times.append(start.timestamp())
                start = _add_months(start, step)
        else:
            first = ceil(low / step) * step
            count = int((high - first) // step) + 1
            if count > max_ticks:
                continue
            times = [first + i * step for i in range(count)]

        if 0 < len(times) <= max_ticks:
            return times, [datetime.fromtimestamp(t, tz=timezone.utc).strftime(label_format) for t in times]

    return [low, high], [datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y") for t in (low, high)]
