from time import sleep
from typing import Callable, List, Optional, TypeVar

from pydantic import BaseModel
from tqdm import tqdm

T = TypeVar("T")


class Interval(BaseModel):
    # The duration of the interval
    interval_seconds: float

    # The amount of times the interval is supposed to be used
    interval_uses: int


class TaskManager:
    """The TaskManager contains utilities to handle long-running tasks."""

    def poll(self,
             make_request: Callable[[], T],
             is_done: Callable[[T], bool],
             get_progress: Optional[Callable[[T], float]] = None) -> T:
        """Continuously poll for data until we got what we need.

        When running certain tasks we need to continuously call the API to retrieve
        new information and to see if the task is completed. To prevent making
        thousands of requests when waiting for long-running tasks to complete we
        poll at varying intervals, starting from 250ms up to 10,000ms. This reduces
        the amount of requests being made while still delivering results swiftly if
        the task is done quickly.

        :param make_request: a function which should request the latest data from the API
        :param is_done: a function which checks if the data returned by make_request indicates the task is done
        :param get_progress: an optional function which should return the progress between 0.0 and 1.0 of the task based on the latest data
        :return: the last return value from make_request when is_done returns True
        """
        # The comments below assume the API call is instant to make the chosen intervals clearer
        intervals: List[Interval] = [
            # 4 requests per second for the first second
            Interval(interval_seconds=0.25, interval_uses=4),
            # 1 request per second for the following 9 seconds
            Interval(interval_seconds=1, interval_uses=9),
            # 1 request per 2 seconds for the following 20 seconds
            Interval(interval_seconds=2, interval_uses=10),
            # 1 request per 5 seconds for the following 4.5 minutes
            Interval(interval_seconds=5, interval_uses=54),
            # 1 request per 10 seconds for the rest of the task
            Interval(interval_seconds=10, interval_uses=1e9)
        ]

        poll_counter = 0
        current_interval_index = 0

        progress_bar = None
        if get_progress is not None:
            progress_bar = tqdm(total=1.0, ncols=50, bar_format="{l_bar}{bar}|")

        while True:
            try:
                data = make_request()
            except Exception as ex:
                if progress_bar is not None:
                    progress_bar.close()
                raise ex

            if get_progress is not None:
                progress_bar.update(get_progress(data) - progress_bar.n)

            if is_done(data):
                if progress_bar is not None:
                    progress_bar.close()
                return data

            sleep(intervals[current_interval_index].interval_seconds)

            poll_counter += 1
            if poll_counter == intervals[current_interval_index].interval_uses:
                current_interval_index += 1
                poll_counter = 0
