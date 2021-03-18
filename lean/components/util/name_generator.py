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

from random import choice


class NameGenerator:
    """The NameGenerator generates random names."""

    def __init__(self) -> None:
        """Creates a new NameGenerator instance."""
        self._verbs = ["Determined", "Pensive", "Adaptable", "Calculating", "Logical", "Energetic", "Creative",
                       "Smooth", "Calm", "Hyper-Active", "Measured", "Fat", "Emotional", "Crying", "Jumping",
                       "Swimming", "Crawling", "Dancing", "Focused", "Well Dressed", "Retrospective", "Hipster",
                       "Square", "Upgraded", "Ugly", "Casual", "Formal", "Geeky", "Virtual", "Muscular", "Alert",
                       "Sleepy"]

        self._colors = ["Red", "Red-Orange", "Orange", "Yellow", "Tan", "Yellow-Green", "Yellow-Green",
                        "Fluorescent Orange", "Apricot", "Green", "Fluorescent Pink", "Sky Blue", "Fluorescent Yellow",
                        "Asparagus", "Blue", "Violet", "Light Brown", "Brown", "Magenta", "Black"]

        self._animals = ["Horse", "Zebra", "Whale", "Tapir", "Barracuda", "Cow", "Cat", "Wolf", "Hamster", "Monkey",
                         "Pelican", "Snake", "Albatross", "Viper", "Guanaco", "Anguilline", "Badger", "Dogfish", "Duck",
                         "Butterfly", "Gaur", "Rat", "Termite", "Eagle", "Dinosaur", "Pig", "Seahorse", "Hornet",
                         "Koala", "Hippopotamus", "Cormorant", "Jackal", "Rhinoceros", "Panda", "Elephant", "Penguin",
                         "Beaver", "Hyena", "Parrot", "Crocodile", "Baboon", "Pony", "Chinchilla", "Fox", "Lion",
                         "Mosquito", "Cobra", "Mule", "Coyote", "Alligator", "Pigeon", "Antelope", "Goat", "Falcon",
                         "Owlet", "Llama", "Gull", "Chicken", "Caterpillar", "Giraffe", "Rabbit", "Flamingo", "Caribou",
                         "Goshawk", "Galago", "Bee", "Jellyfish", "Buffalo", "Salmon", "Bison", "Dolphin", "Jaguar",
                         "Dog", "Armadillo", "Gorilla", "Alpaca", "Kangaroo", "Dragonfly", "Salamander", "Owl", "Bat",
                         "Sheep", "Frog", "Chimpanzee", "Bull", "Scorpion", "Lemur", "Camel", "Leopard", "Fish",
                         "Donkey", "Manatee", "Shark", "Bear", "kitten", "Fly", "Ant", "Sardine"]

    def generate_name(self) -> str:
        """Returns a random name.

        :return: a random name containing multiple words
        """
        return f"{choice(self._verbs)} {choice(self._colors)} {choice(self._animals)}"
