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

from pathlib import Path

def _capitalize(word: str) -> str:
    """Capitalizes the given word.

    :param word: the word to capitalize
    :return: the word with the first letter capitalized (any other uppercase characters are preserved)
    """
    if word == "":
        return word
    return word[0].upper() + word[1:]


def convert_to_class_name(file_path: Path):
    """Converts the project name into a valid class name by removing all non-alphanumeric characters

    :param file_path: Path to the root project
    :return: returns a valid class name
    """
    from re import sub
    return sub(f"[^a-zA-Z0-9]", "", "".join(map(_capitalize, file_path.name.split(" "))))
