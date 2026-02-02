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
    # Pydantic v1 - use direct imports
    from pydantic import BaseModel, ValidationError, Field, validator
    field_validator = None  # Not available in v1
else:
    # Pydantic v2 - use native v2 API (required for Python 3.14+)
    from pydantic import BaseModel, ValidationError, Field, field_validator

    # Provide a validator alias for backwards compatibility during migration
    # This is a simple wrapper that converts v1-style validators to v2-style
    def validator(*fields, pre=False, **kwargs):
        """Backwards-compatible validator wrapper for Pydantic v2."""
        mode = 'before' if pre else 'after'
        def decorator(func):
            return field_validator(*fields, mode=mode, **kwargs)(classmethod(func))
        return decorator

class WrappedBaseModel(BaseModel):
    """A version of Pydantic's BaseModel which makes the input data accessible in case of a validation error."""

    if not pydantic_version.startswith("1."):
        model_config = {"extra": "ignore"}

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
