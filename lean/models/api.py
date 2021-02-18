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

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


# The models in this module are all parts of responses from the QuantConnect API
# The keys of properties are not changed so they don't obey the rest of the project's naming conventions

class QCCollaborator(BaseModel):
    id: int
    uid: int
    blivecontrol: bool
    epermission: str
    profileimage: str
    name: str
    owner: bool = False


class QCParameter(BaseModel):
    key: str
    value: str
    min: Optional[float]
    max: Optional[float]
    step: Optional[float]
    type: Optional[str]


class QCLiveResults(BaseModel):
    eStatus: str
    sDeployID: Optional[str] = None
    sServerType: Optional[str] = None
    dtLaunched: Optional[datetime] = None
    dtStopped: Optional[datetime] = None
    sBrokerage: Optional[str] = None
    sSecurityTypes: Optional[str] = None
    dUnrealized: Optional[float] = None
    dfees: Optional[float] = None
    dnetprofit: Optional[float] = None
    dEquity: Optional[float] = None
    dHoldings: Optional[float] = None
    dCapital: Optional[float] = None
    dVolume: Optional[float] = None
    iTrades: Optional[int] = None
    sErrorMessage: Optional[str] = None


class QCLanguage(str, Enum):
    CSharp = "C#"
    FSharp = "F#"
    VisualBasic = "VB"
    Java = "Ja"
    Python = "Py"


class QCProject(BaseModel):
    projectId: int
    organizationId: str
    name: str
    description: str
    modified: datetime
    created: datetime
    language: QCLanguage
    collaborators: List[QCCollaborator]
    leanVersionId: int
    leanPinnedToMaster: bool
    parameters: List[QCParameter]
    liveResults: QCLiveResults
    libraries: List[int]


class QCCreatedProject(BaseModel):
    projectId: int
    name: str
    modified: datetime
    created: datetime


class QCFullFile(BaseModel):
    name: str
    content: str
    modified: datetime
    isLibrary: bool


class QCMinimalFile(BaseModel):
    name: str
    content: str
    modified: datetime


class QCCompileParameter(BaseModel):
    line: int
    type: str


class QCCompileParameterContainer(BaseModel):
    file: str
    parameters: List[QCCompileParameter]


class QCCompileState(str, Enum):
    InQueue = "InQueue"
    BuildSuccess = "BuildSuccess"
    BuildError = "BuildError"


class QCCompileWithLogs(BaseModel):
    compileId: str
    state: QCCompileState
    logs: List[str]


class QCCompileWithParameters(BaseModel):
    compileId: str
    state: QCCompileState
    parameters: List[QCCompileParameterContainer]


class QCBacktest(BaseModel):
    backtestId: str
    projectId: int
    status: str
    name: str
    note: Optional[str] = None
    created: datetime
    completed: bool
    progress: float
    result: Optional[Any] = None
    error: Optional[str] = None
    stacktrace: Optional[str] = None
    runtimeStatistics: Optional[Dict[str, str]]
    statistics: Optional[Union[Dict[str, str], List[Any]]]
    totalPerformance: Optional[Any]

    def is_complete(self) -> bool:
        """Returns whether the backtest has completed in the cloud.

        :return: True if the backtest is complete, False if not
        """
        if self.error is not None:
            return True

        if not self.completed:
            return False

        has_runtime_statistics = self.runtimeStatistics is not None
        has_statistics = self.statistics is not None and not isinstance(self.statistics, list)
        return has_runtime_statistics and has_statistics

    def get_url(self) -> str:
        """Returns the url of the backtests results page in the cloud.

        :return: a url which when visited opens an Algorithm Lab tab containing the backtest's results
        """
        return f"https://www.quantconnect.com/terminal/#open/{self.projectId}/{self.backtestId}"


class QCBacktestReport(BaseModel):
    report: str


class QCNodePrice(BaseModel):
    monthly: int
    yearly: int


class QCNode(BaseModel):
    id: str
    name: str
    projectName: str
    description: str
    usedBy: str
    sku: str
    busy: bool
    price: QCNodePrice
    speed: float
    cpu: int
    ram: float
    assets: int
    host: Optional[str]


class QCNodeList(BaseModel):
    backtest: List[QCNode]
    research: List[QCNode]
    live: List[QCNode]


class QCLiveAlgorithmStatus(str, Enum):
    DeployError = "DeployError"
    InQueue = "InQueue"
    Running = "Running"
    Stopped = "Stopped"
    Liquidated = "Liquidated"
    Deleted = "Deleted"
    Completed = "Completed"
    RuntimeError = "RuntimeError"
    Invalid = "Invalid"
    LoggingIn = "LoggingIn"
    Initializing = "Initializing"
    History = "History"


class QCLiveAlgorithm(BaseModel):
    projectId: int
    deployId: str
    status: QCLiveAlgorithmStatus
    launched: datetime
    stopped: Optional[datetime]
    brokerage: str
    subscription: str
    error: str


class QCCard(BaseModel):
    brand: str
    expiration: str
    last4: str


class QCOrganization(BaseModel):
    organizationId: str
    creditBalance: float
    card: QCCard
