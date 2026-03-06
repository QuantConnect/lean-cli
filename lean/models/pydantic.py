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
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, ValidationError, Field, field_validator

# Path field that accepts str | Path. Converts in Python before pydantic-core runs,
# avoiding issues when pathlib is patched at runtime (e.g. pyfakefs).
SafePath = Annotated[Path, BeforeValidator(lambda v: v if isinstance(v, Path) else Path(v))]


class WrappedBaseModel(BaseModel):
    """A version of Pydantic's BaseModel which makes the input data accessible in case of a validation error."""

    # Ensures backward compatibility: automatically converts numeric inputs to strings for string fields
    model_config = ConfigDict(coerce_numbers_to_str=True)
