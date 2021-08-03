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

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import validator
from rich import box
from rich.table import Table
from rich.text import Text

from lean.constants import SECURITY_MASTER_PRODUCT_ID
from lean.models.pydantic import WrappedBaseModel


# The models in this module are all parts of responses from the QuantConnect API
# The keys of properties are not changed, so they don't obey the rest of the project's naming conventions


class QCCollaborator(WrappedBaseModel):
    id: int
    uid: int
    blivecontrol: bool
    epermission: str
    profileimage: str
    name: str
    owner: bool = False


class QCParameter(WrappedBaseModel):
    key: str
    value: str
    min: Optional[float]
    max: Optional[float]
    step: Optional[float]
    type: Optional[str]


class QCLiveResults(WrappedBaseModel):
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


class QCProject(WrappedBaseModel):
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

    @validator("parameters", pre=True)
    def process_parameters_dict(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return list(value.values())
        return value

    def get_url(self) -> str:
        """Returns the url of the project page in the cloud.

        :return: a url which when visited opens an Algorithm Lab tab containing the project
        """
        return f"https://www.quantconnect.com/project/{self.projectId}"


class QCCreatedProject(WrappedBaseModel):
    projectId: int
    name: str
    modified: datetime
    created: datetime


class QCFullFile(WrappedBaseModel):
    name: str
    content: str
    modified: datetime
    isLibrary: bool


class QCMinimalFile(WrappedBaseModel):
    name: str
    content: str
    modified: datetime


class QCCompileParameter(WrappedBaseModel):
    line: int
    type: str


class QCCompileParameterContainer(WrappedBaseModel):
    file: str
    parameters: List[QCCompileParameter]


class QCCompileState(str, Enum):
    InQueue = "InQueue"
    BuildSuccess = "BuildSuccess"
    BuildError = "BuildError"


class QCCompileWithLogs(WrappedBaseModel):
    compileId: str
    state: QCCompileState
    logs: List[str]


class QCCompileWithParameters(WrappedBaseModel):
    compileId: str
    state: QCCompileState
    parameters: List[QCCompileParameterContainer]


class QCBacktest(WrappedBaseModel):
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

    def get_statistics_table(self) -> Table:
        """Converts the statistics into a pretty table.

        :return: a table containing all statistics
        """
        stats = []

        for key, value in self.runtimeStatistics.items():
            stats.append(key)

            if "-" in value:
                stats.append(Text.from_markup(f"[red]{value}[/red]"))
            elif any(char.isdigit() and int(char) > 0 for char in value):
                stats.append(Text.from_markup(f"[green]{value}[/green]"))
            else:
                stats.append(value)

        if len(stats) % 4 != 0:
            stats.extend(["", ""])

        end_of_first_section = len(stats)

        for key, value in self.statistics.items():
            stats.extend([key, value])

        if len(stats) % 4 != 0:
            stats.extend(["", ""])

        table = Table(box=box.SQUARE)
        table.add_column("Statistic", overflow="fold")
        table.add_column("Value", overflow="fold")
        table.add_column("Statistic", overflow="fold")
        table.add_column("Value", overflow="fold")

        for i in range(int(len(stats) / 4)):
            start = i * 4
            end = (i + 1) * 4
            table.add_row(*stats[start:end], end_section=end_of_first_section == end)

        return table


class QCBacktestReport(WrappedBaseModel):
    report: str


class QCNodePrice(WrappedBaseModel):
    monthly: int
    yearly: int


class QCNode(WrappedBaseModel):
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


class QCNodeList(WrappedBaseModel):
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


class QCMinimalLiveAlgorithm(WrappedBaseModel):
    projectId: int
    deployId: str
    status: Optional[QCLiveAlgorithmStatus] = None

    def get_url(self) -> str:
        """Returns the url of the live deployment in the cloud.

        :return: a url which when visited opens an Algorithm Lab tab containing the live deployment
        """
        return f"https://www.quantconnect.com/project/{self.projectId}/live"


class QCFullLiveAlgorithm(QCMinimalLiveAlgorithm):
    projectId: int
    deployId: str
    status: Optional[QCLiveAlgorithmStatus] = None
    launched: datetime
    stopped: Optional[datetime]
    brokerage: str
    subscription: str
    error: str


class QCEmailNotificationMethod(WrappedBaseModel):
    address: str
    subject: str


class QCWebhookNotificationMethod(WrappedBaseModel):
    address: str
    headers: Dict[str, str]


class QCSMSNotificationMethod(WrappedBaseModel):
    phoneNumber: str


QCNotificationMethod = Union[QCEmailNotificationMethod, QCWebhookNotificationMethod, QCSMSNotificationMethod]


class QCCard(WrappedBaseModel):
    brand: str
    expiration: str
    last4: str


class QCAccount(WrappedBaseModel):
    organizationId: str
    card: Optional[QCCard] = None

    # Balance in QCC
    creditBalance: float


class QCOrganizationCreditMovement(WrappedBaseModel):
    date: str
    description: str
    type: str
    subtype: str
    amount: float

    # Balance in QCC
    balance: float


class QCOrganizationCredit(WrappedBaseModel):
    movements: List[QCOrganizationCreditMovement]

    # Balance in QCC
    balance: float


class QCOrganizationProductItem(WrappedBaseModel):
    productId: int
    name: str
    quantity: int
    unitPrice: float
    total: float


class QCOrganizationProduct(WrappedBaseModel):
    name: str
    items: List[QCOrganizationProductItem]


class QCOrganizationData(WrappedBaseModel):
    signedTime: Optional[int]
    current: bool


class QCOrganizationMember(WrappedBaseModel):
    id: int
    name: str
    isAdmin: bool
    email: str


class QCFullOrganization(WrappedBaseModel):
    id: str
    name: str
    seats: int
    type: str
    credit: QCOrganizationCredit
    products: List[QCOrganizationProduct]
    data: QCOrganizationData
    members: List[QCOrganizationMember]

    def has_security_master_subscription(self) -> bool:
        """Returns whether this organization has a Security Master subscription.

        :return: True if the organization has a Security Master subscription, False if not
        """
        data_products_product = next((x for x in self.products if x.name == "Data"), None)
        if data_products_product is None:
            return False

        return any(x.productId == SECURITY_MASTER_PRODUCT_ID for x in data_products_product.items)


class QCMinimalOrganization(WrappedBaseModel):
    id: str
    name: str
    type: str
    ownerName: str
    members: int
    preferred: bool


class QCSecurityType(str, Enum):
    Equity = "Equity"
    Forex = "Forex"
    CFD = "Cfd"
    Future = "Future"
    Crypto = "Crypto"
    Option = "Option"
    FutureOption = "FutureOption"


class QCResolution(str, Enum):
    Tick = "Tick"
    Second = "Second"
    Minute = "Minute"
    Hour = "Hour"
    Daily = "Daily"

    @classmethod
    def by_name(cls, name: str) -> 'QCResolution':
        """Returns the enum member with the same name as the given one, case insensitively.

        :param name: the name of the enum member (case insensitive)
        :return: the matching enum member
        """
        for k, v in cls.__members__.items():
            if k.lower() == name.lower():
                return v
        raise ValueError(f"QCResolution has no member named '{name}'")


class QCLink(WrappedBaseModel):
    link: str


class QCOptimizationBacktest(WrappedBaseModel):
    id: str
    name: str
    exitCode: int
    parameterSet: Dict[str, str]
    statistics: List[float] = []


class QCOptimization(WrappedBaseModel):
    optimizationId: str
    projectId: int
    status: str
    name: str
    backtests: Dict[str, QCOptimizationBacktest] = {}
    runtimeStatistics: Dict[str, str] = {}

    @validator("backtests", "runtimeStatistics", pre=True)
    def parse_empty_lists(cls, value: Any) -> Any:
        # If these fields have no data, they are assigned an array by default
        # For consistency we convert those empty arrays to empty dicts
        if isinstance(value, list):
            return {}
        return value

    def get_progress(self) -> float:
        """Returns the progress of the optimization between 0.0 and 1.0.

        :return: 0.0 if the optimization is 0% done, 1.0 if the optimization is 100% done, or somewhere in between
        """
        stats = self.runtimeStatistics
        if "Completed" in stats and "Failed" in stats and "Total" in stats:
            finished_backtests = float(stats["Completed"]) + float(stats["Failed"])
            total_backtests = float(stats["Total"])
            return finished_backtests / total_backtests
        return 0.0


class QCOptimizationEstimate(WrappedBaseModel):
    estimateId: str
    time: int
    balance: int


class QCDataVendor(WrappedBaseModel):
    vendorName: str
    regex: Any

    # Price in QCC
    price: Optional[float]

    @validator("regex", pre=True)
    def parse_regex(cls, value: Any) -> Any:
        if isinstance(value, str):
            return re.compile(value[value.index("/") + 1:value.rindex("/")])
        return value


class QCDataInformation(WrappedBaseModel):
    datasources: Dict[str, Any]
    prices: List[QCDataVendor]
    agreement: str


class QCDatasetDelivery(str, Enum):
    CloudOnly = "cloud only"
    DownloadOnly = "download only"
    CloudAndDownload = "cloud & download"


class QCDatasetTag(WrappedBaseModel):
    name: str


class QCDataset(WrappedBaseModel):
    id: int
    name: str
    delivery: QCDatasetDelivery
    vendorName: str
    tags: List[QCDatasetTag]


class QCUser(WrappedBaseModel):
    name: str
    profile: str
    badge: Optional[str]


class QCTerminalNewsItem(WrappedBaseModel):
    id: int
    type: str
    category: str
    title: str
    content: str
    image: str
    link: str
    year_deleted: Optional[Any]
    week_deleted: Optional[Any]
    created: datetime
    date: datetime
