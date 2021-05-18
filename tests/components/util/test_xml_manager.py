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

from lean.components.util.xml_manager import XMLManager


def test_parse_parses_xml_string() -> None:
    xml_string = """
<Person>
    <!-- Person name -->
    <Name>John Doe</Name>
    <Email/>
</Person>
    """

    xml_manager = XMLManager()
    xml_tree = xml_manager.parse(xml_string)

    assert xml_tree.find(".//Name") is not None
    assert xml_tree.find(".//Email") is not None

    assert xml_tree.find(".//Name").text == "John Doe"


def test_to_string_turns_xml_element_into_pretty_string() -> None:
    xml_manager = XMLManager()

    xml_string = """
<Person>
    <!-- Person name -->
    <Name>John Doe</Name>
    <Email/>
</Person>
    """.strip() + "\n"

    assert xml_manager.to_string(xml_manager.parse(xml_string)) == xml_string
