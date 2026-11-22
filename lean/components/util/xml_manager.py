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

from lxml import etree


class XMLManager:
    """The PathManager class provides utilities for working with XML."""

    def __init__(self) -> None:
        """Creates a new XMLManager instance."""
        self._xml_parser = etree.XMLParser(remove_blank_text=True, encoding="utf-8")

    def parse(self, xml_string: str) -> etree.Element:
        """Parses an XML string to an XML element.

        :param xml_string: the string to parse
        :return: the parsed XML element
        """
        return etree.fromstring(xml_string.encode("utf-8"), parser=self._xml_parser)

    def to_string(self, root: etree.Element) -> str:
        """Turns an XML element into a pretty string.

        :param root: the XML element to turn into a string
        :return: the XML element as a pretty string using 4 spaces as indentation
        """
        etree.indent(root, " " * 4)
        return etree.tostring(root, encoding="utf-8", method="xml", pretty_print=True).decode("utf-8")

    def unconditional_item_group(self, root: etree.Element) -> etree.Element:
        """Returns a project ItemGroup with no Condition, creating one when none exists.

        Direct children only: an ItemGroup inside a Target is not a project reference group.
        A Condition on the group would limit a new reference to that configuration.

        :param root: the parsed csproj element
        :return: an ItemGroup that is included in every build configuration
        """
        project = root if str(root.tag).rsplit("}", 1)[-1] == "Project" else root.find(".//Project")
        if project is None:
            project = root

        for item_group in reversed(project.findall("ItemGroup")):
            if item_group.get("Condition") is None:
                return item_group

        return etree.SubElement(project, "ItemGroup")
