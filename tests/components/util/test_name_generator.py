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

from lean.components.util.name_generator import NameGenerator


def test_generate_name_generates_names_with_at_least_three_words() -> None:
    name_generator = NameGenerator()
    name = name_generator.generate_name()

    assert name.count(" ") >= 2


def test_generate_name_generates_names_randomly() -> None:
    name_generator = NameGenerator()
    draws = ["Calm", "Blue", "Fox", "Geeky", "Red", "Owl"]

    with mock.patch("random.choice", side_effect=draws) as choice:
        assert name_generator.generate_name() == "Calm Blue Fox"
        assert name_generator.generate_name() == "Geeky Red Owl"

    assert choice.call_count == len(draws)
    assert all(draw in call.args[0] for call, draw in zip(choice.call_args_list, draws))
