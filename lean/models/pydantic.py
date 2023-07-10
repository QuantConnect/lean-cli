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

from pydantic import __version__ as pydantic_version
if pydantic_version.startswith("1."):
    # We keep all this imports here, even if not used like validator, so other files can import them through this file
    # to avoid having to check the pydantic version in every file.
    # All imports should be done through this file to avoid pydantic version related errors.
    from pydantic import BaseModel, ValidationError, Field, validator
else:
    from pydantic.v1 import BaseModel, ValidationError, Field, validator

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
