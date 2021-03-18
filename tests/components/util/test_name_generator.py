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

from lean.components.util.name_generator import NameGenerator


def test_generate_name_generates_names_with_at_least_three_words() -> None:
    name_generator = NameGenerator()
    name = name_generator.generate_name()

    assert name.count(" ") >= 2


def test_generate_name_generates_names_randomly() -> None:
    name_generator = NameGenerator()

    assert name_generator.generate_name() != name_generator.generate_name()
