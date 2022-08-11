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

import os
import json
import requests
from pathlib import Path

json_modules = {}
file_name = "modules-1.3.json"
dirname = os.path.dirname(__file__)
file_path = os.path.join(dirname, f'../{file_name}')

# check if new file is avaiable online
url = f"https://cdn.quantconnect.com/cli/{file_name}"
try:
    res = requests.get(url)
    if res.ok:
        new_content = res.json()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(new_content, f, ensure_ascii=False, indent=4)
except Exception as e:
    # No need to do anything if file isn't avaiable
    pass

# check if file exists
if not Path(file_path).is_file():
    raise FileNotFoundError(
        f"Modules json not found in the given path {file_path}")

with open(file_path) as f:
    data = json.load(f)
    json_modules = data['modules']
