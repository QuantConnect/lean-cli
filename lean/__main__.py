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

# Allows running the CLI with `python -m lean`, which is how `lean ui` launches commands as child processes

import signal

# `lean ui` starts commands in their own process group on Windows and stops them with Ctrl+Break,
# which is turned into Ctrl+C here so the command's own Ctrl+C handling (e.g. stopping its Docker container) runs
if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, lambda *_: signal.raise_signal(signal.SIGINT))

from lean.main import main

main(prog_name="lean")
