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

from pydantic import BaseModel, ValidationError


class WrappedBaseModel(BaseModel):
    """A version of Pydantic's BaseModel which makes the input data accessible in case of a validation error."""

    def __init__(self, *args, **kwargs) -> None:
        """Creates a new WrappedBaseModel instance.

        :param args: args to pass on to the BaseModel constructor
        :param kwargs: kwargs to pass on to the BaseModel constructor
        """
        try:
            super().__init__(*args, **kwargs)
        except ValidationError as error:
            error.input_value = kwargs
            raise error
