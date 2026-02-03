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

# Note: Pydantic v1 (including pydantic.v1 compatibility layer) is NOT compatible with Python 3.14+
# due to PEP 649/749 changes to annotation evaluation. This module uses native pydantic v2 API.
# See: https://pydantic.dev/articles/pydantic-v2-12-release

from pydantic import BaseModel, ValidationError, Field, field_validator, ConfigDict

# Re-export for backwards compatibility with existing imports
# Note: `validator` is deprecated in v2, use `field_validator` instead
# For modules that import validator, provide field_validator as an alias
validator = field_validator


class WrappedBaseModel(BaseModel):
    """A version of Pydantic's BaseModel which makes the input data accessible in case of a validation error."""
    
    # Allow extra fields and arbitrary types for backwards compatibility with v1 behavior
    model_config = ConfigDict(
        extra='ignore',
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow both alias and field name (v1: allow_population_by_field_name)
    )

    def __init__(self, *args, **kwargs) -> None:
        """Creates a new WrappedBaseModel instance.

        :param args: args to pass on to the BaseModel constructor
        :param kwargs: kwargs to pass on to the BaseModel constructor
        """
        try:
            super().__init__(*args, **kwargs)
        except ValidationError as error:
            # In pydantic v2, we need to attach input_value differently
            # Store it as a custom attribute on the error
            object.__setattr__(error, 'input_value', kwargs)
            raise error
