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

def rename_internal_config_to_user_friendly_format(key: str) -> str:
    """
    Function to rename a string if it matches a specific key.

    Parameters:
    key (str): The input string.

    Returns:
    str: The renamed string if it matches the specific key and passes the validation,
         otherwise returns the original string.
    """
    if key is None or len(key) == 0:
        raise ValueError("Input string is null or empty")
    
    # Check if the input string matches the specific key
    if key == "data-queue-handler":
        return "data-provider-live"
    else:
        return key

    