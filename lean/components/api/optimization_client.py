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

from typing import List

from lean.components.api.api_client import *
from lean.models.api import QCOptimization, QCOptimizationEstimate
from lean.models.optimizer import OptimizationConstraint, OptimizationParameter, OptimizationTarget


class OptimizationClient:
    """The OptimizationClient class contains methods to interact with optimizations/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new OptimizationClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get(self, optimization_id: str) -> QCOptimization:
        """Returns the details of an optimization.

        :param optimization_id: the id of the optimization to retrieve the details of
        :return: the details of the specified optimization
        """
        data = self._api.post("optimizations/read", {"optimizationId": optimization_id}, data_as_json=False)
        return QCOptimization(**data["optimization"])

    def create(self,
               project_id: int,
               compile_id: str,
               name: str,
               strategy: str,
               target: OptimizationTarget,
               parameters: List[OptimizationParameter],
               constraints: List[OptimizationConstraint],
               node_type: str,
               parallel_nodes: int) -> QCOptimization:
        """Creates a new optimization.

        :param project_id: the id of the project to optimize
        :param compile_id: the id of the compile to optimize
        :param name: the name of the optimization
        :param strategy: the strategy to optimize with
        :param target: the target of the optimization
        :param parameters: the parameters to optimize
        :param constraints: the constraints of the optimization
        :param node_type: the type of the node to run the optimization on
        :param parallel_nodes: the number of parallel nodes to run the optimization on
        :return: the created optimization
        """
        request_parameters = self._build_request_parameters(project_id,
                                                            compile_id,
                                                            name,
                                                            strategy,
                                                            target,
                                                            parameters,
                                                            constraints,
                                                            node_type,
                                                            parallel_nodes)

        data = self._api.post("optimizations/create", request_parameters, data_as_json=False)
        return QCOptimization(**data["optimizations"][0])

    def abort(self, optimization_id: str) -> None:
        """Aborts a running optimization.

        :param optimization_id: the id of the optimization to abort
        """
        self._api.post("optimizations/abort", {"optimizationId": optimization_id}, data_as_json=False)

    def delete(self, optimization_id: str) -> None:
        """Deletes an optimization.

        :param optimization_id: the id of the optimization to delete
        """
        self._api.post("optimizations/delete", {"optimizationId": optimization_id}, data_as_json=False)

    def estimate(self,
                 project_id: int,
                 compile_id: str,
                 name: str,
                 strategy: str,
                 target: OptimizationTarget,
                 parameters: List[OptimizationParameter],
                 constraints: List[OptimizationConstraint],
                 node_type: str,
                 parallel_nodes: int) -> QCOptimizationEstimate:
        """Estimates how long a backtest will take.

        :param project_id: the id of the project to optimize
        :param compile_id: the id of the compile to optimize
        :param name: the name of the optimization
        :param strategy: the strategy to optimize with
        :param target: the target of the optimization
        :param parameters: the parameters to optimize
        :param constraints: the constraints of the optimization
        :param node_type: the type of the node to run the optimization on
        :param parallel_nodes: the number of parallel nodes to run the optimization on
        :return: the resulting estimation
        """
        request_parameters = self._build_request_parameters(project_id,
                                                            compile_id,
                                                            name,
                                                            strategy,
                                                            target,
                                                            parameters,
                                                            constraints,
                                                            node_type,
                                                            parallel_nodes)

        data = self._api.post("optimizations/estimate", request_parameters, data_as_json=False)
        return QCOptimizationEstimate(**data["estimate"])

    def _build_request_parameters(self,
                                  project_id: int,
                                  compile_id: str,
                                  name: str,
                                  strategy: str,
                                  target: OptimizationTarget,
                                  parameters: List[OptimizationParameter],
                                  constraints: List[OptimizationConstraint],
                                  node_type: str,
                                  parallel_nodes: int) -> Dict[str, Any]:
        """Creates the request parameters object used when creating and estimating optimizations.

        :param project_id: the id of the project to optimize
        :param compile_id: the id of the compile to optimize
        :param name: the name of the optimization
        :param strategy: the strategy to optimize with
        :param target: the target of the optimization
        :param parameters: the parameters to optimize
        :param constraints: the constraints of the optimization
        :param node_type: the type of the node to run the optimization on
        :param parallel_nodes: the number of parallel nodes to run the optimization on
        :return: the object containing all parameters expected by the create and estimate endpoints
        """
        request_parameters = {
            "projectId": project_id,
            "compileId": compile_id,
            "name": name,
            "strategy": strategy,
            "target": target.target,
            "targetTo": target.extremum.value,
            "targetValue": "",
            "nodeType": node_type,
            "parallelNodes": parallel_nodes,
            "estimatedCost": "0.01"
        }

        for index, parameter in enumerate(parameters):
            request_parameters[f"parameters[{index}][key]"] = parameter.name
            request_parameters[f"parameters[{index}][min]"] = parameter.min
            request_parameters[f"parameters[{index}][max]"] = parameter.max
            request_parameters[f"parameters[{index}][step]"] = parameter.step

        for index, constraint in enumerate(constraints):
            request_parameters[f"constraints[{index}][target]"] = constraint.target
            request_parameters[f"constraints[{index}][operator]"] = constraint.operator.name
            request_parameters[f"constraints[{index}][target-value]"] = constraint.target_value

        return request_parameters
