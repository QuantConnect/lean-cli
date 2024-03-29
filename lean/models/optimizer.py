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

from enum import Enum

from lean.models.pydantic import WrappedBaseModel, Field


class OptimizationExtremum(str, Enum):
    Minimum = "min"
    Maximum = "max"


class OptimizationConstraintOperator(str, Enum):
    Less = "less"
    LessOrEqual = "lessOrEqual"
    Greater = "greater"
    GreaterOrEqual = "greaterOrEqual"
    Equals = "equals"
    NotEqual = "notEqual"


class OptimizationTarget(WrappedBaseModel):
    target: str
    extremum: OptimizationExtremum


class OptimizationConstraint(WrappedBaseModel):
    target: str
    operator: OptimizationConstraintOperator
    target_value: float = Field(alias="target-value")

    def __str__(self) -> str:
        operator = {
            OptimizationConstraintOperator.Less: "<",
            OptimizationConstraintOperator.LessOrEqual: "<=",
            OptimizationConstraintOperator.Greater: ">",
            OptimizationConstraintOperator.GreaterOrEqual: ">=",
            OptimizationConstraintOperator.Equals: "==",
            OptimizationConstraintOperator.NotEqual: "!=",
        }[self.operator]

        return f"{self.target} {operator} {self.target_value}"


class OptimizationParameter(WrappedBaseModel):
    name: str
    min: float
    max: float
    step: float
