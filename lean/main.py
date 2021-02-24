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

import sys
import traceback

from lean.commands import lean
from lean.container import container


def main() -> None:
    """This function is the entrypoint when running a Lean command in a terminal."""
    try:
        lean.main()
    except Exception as exception:
        logger = container.logger()
        logger.debug(traceback.format_exc().strip())
        logger.error(f"Error: {exception}")
        sys.exit(1)
