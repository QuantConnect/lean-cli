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

from lean.models.pydantic import WrappedBaseModel, validator


# The models in this module are all parts of responses from the QuantConnect API
# The keys of properties are not changed, so they don't obey the rest of the project's naming conventions


class QCAuth0Authorization(WrappedBaseModel):
    authorization: Optional[Dict[str, Any]]

    def get_account_ids(self) -> List[str]:
        """
        Retrieves a list of account IDs from the list of Account objects.

        This method returns only the 'id' values from each account in the 'accounts' list.
        If there are no accounts, it returns an empty list.

        Returns:
            List[str]: A list of account IDs.
        """
        accounts = self.authorization.get('accounts', [])
        return [account["id"] for account in accounts] if accounts else []

    def get_authorization_config_without_account(self) -> Dict[str, str]:
        """
        Returns the authorization data without the 'accounts' key.

        Iterates through the 'authorization' dictionary and excludes the 'accounts' entry.

        Returns:
            Dict[str, str]: Authorization details excluding 'accounts'.
        """
        return {key: value for key, value in self.authorization.items() if key != 'accounts'}


class ProjectEncryptionKey(WrappedBaseModel):
    id: str
    name: str

class QCCollaborator(WrappedBaseModel):
    uid: int
    liveControl: bool
    permission: str
    profileImage: str
    name: str
    owner: bool = False


class QCParameter(WrappedBaseModel):
    key: str
    value: str
    min: Optional[float]
    max: Optional[float]
    step: Optional[float]
    type: Optional[str]


class QCLanguage(str, Enum):
    CSharp = "C#"
    FSharp = "F#"
    VisualBasic = "VB"
    Java = "Ja"
    Python = "Py"


class QCProjectLibrary(WrappedBaseModel):
    projectId: int
    libraryName: str
    ownerName: str
    access: bool

    def __hash__(self):
        return hash(self.projectId)

    def __eq__(self, other: Any):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.projectId == other.projectId


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
    leanEnvironment: int
    parameters: List[QCParameter]
    libraries: List[QCProjectLibrary]
    encrypted: Optional[bool] = False
    encryptionKey: Optional[ProjectEncryptionKey] = None

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

    def __hash__(self):
        return hash(self.projectId)

    def __eq__(self, other: Any):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.projectId == other.projectId


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


class QCCompileState(str, Enum):
    InQueue = "InQueue"
    BuildSuccess = "BuildSuccess"
    BuildError = "BuildError"


class QCCompile(WrappedBaseModel):
    compileId: str
    state: QCCompileState


class QCCompileWithLogs(QCCompile):
    logs: List[str]


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
        return f"https://www.quantconnect.com/project/{self.projectId}/{self.backtestId}"

    def get_statistics_table(self):
        """Converts the statistics into a pretty table.

        :return: a table containing all statistics
        """
        from rich import box
        from rich.table import Table
        from rich.text import Text

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


class QCRestResponse(WrappedBaseModel):
    success: bool
    error: Optional[List[str]]

class QCMinimalLiveAlgorithm(WrappedBaseModel):
    projectId: int
    deployId: str
    status: Optional[QCLiveAlgorithmStatus] = None

    def get_url(self) -> str:
        """Returns the url of the live deployment in the cloud.

        :return: an url which when visited opens an Algorithm Lab tab containing the live deployment
        """
        return f"https://www.quantconnect.com/project/{self.projectId}/live"


class QCFullLiveAlgorithm(QCMinimalLiveAlgorithm):
    projectId: int
    deployId: str
    status: Optional[QCLiveAlgorithmStatus] = None
    launched: datetime
    stopped: Optional[datetime]
    brokerage: str


class QCEmailNotificationMethod(WrappedBaseModel):
    address: str
    subject: str


class QCWebhookNotificationMethod(WrappedBaseModel):
    address: str
    headers: Dict[str, str]


class QCSMSNotificationMethod(WrappedBaseModel):
    phoneNumber: str


class QCTelegramNotificationMethod(WrappedBaseModel):
    id: str
    token: Optional[str] = None


QCNotificationMethod = Union[QCEmailNotificationMethod, QCWebhookNotificationMethod, QCSMSNotificationMethod, QCTelegramNotificationMethod]


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

    def has_security_master_subscription(self, id: int) -> bool:
        """Returns whether this organization has the Security Master subscription of a given Id

        :param id: the Id of the Security Master Subscription
        :return: True if the organization has a Security Master subscription, False if not
        """

        data_products_product = next((x for x in self.products if x.name == "Data"), None)
        if data_products_product is None:
            return False

        return any(x.productId == id for x in data_products_product.items)


class QCMinimalOrganization(WrappedBaseModel):
    id: str
    name: str
    type: str
    ownerName: str
    members: int
    preferred: bool


class QCDataType(str, Enum):
    Trade = "Trade"
    Quote = "Quote"
    Bulk = "Bulk"
    Universe = "Universe"
    OpenInterest = "OpenInterest"
    Open_Interest = "Open Interest"

    @classmethod
    def get_all_members(cls):
        """
        Retrieve all members (values) of the QCDataType enumeration.

        Returns:
        list: A list containing all the values of the QCDataType enumeration.

        Example:
        >>> all_data_types = QCDataType.get_all_members()
        >>> print(all_data_types)
        ['Trade', 'Quote', 'OpenInterest']
        """
        return list(cls.__members__.values())

    @classmethod
    def get_all_members_except(cls, skip_value:str):
        return [value for value in QCDataType.__members__.values() if value != skip_value]

class QCSecurityType(str, Enum):
    Equity = "Equity"
    Index = "Index"
    Forex = "Forex"
    CFD = "Cfd"
    Future = "Future"
    Crypto = "Crypto"
    CryptoFuture = "CryptoFuture"
    Option = "Option"
    IndexOption = "IndexOption"
    Commodity = "Commodity"
    FutureOption = "FutureOption"

    @classmethod
    def get_all_members(cls):
        """
        Retrieve all members (values) of the QCSecurityType enumeration.

        Returns:
        list: A list containing all the values of the QCSecurityType enumeration.

        Example:
        >>> all_security_types = QCSecurityType.get_all_members()
        >>> print(all_security_types)
        ['Equity', 'Index', 'Forex', 'Cfd', 'Future', 'Crypto', 'CryptoFuture', 'Option', 'IndexOption', 'Commodity', 'FutureOption']
        """
        return list(cls.__members__.values())


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

    @classmethod
    def get_all_members(cls):
        """
        Retrieve all members (values) of the QCResolution enumeration.

        Returns:
        list: A list containing all the values of the QCResolution enumeration.

        Example:
        >>> all_resolutions = QCResolution.get_all_members()
        >>> print(all_resolutions)
        ['Tick', 'Second', 'Minute', 'Hour', 'Daily']
        """
        return list(cls.__members__.values())


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
        from re import compile
        if isinstance(value, str):
            return compile(value[value.index("/") + 1:value.rindex("/")])
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
    pending: bool


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


class QCLeanEnvironment(WrappedBaseModel):
    id: int
    name: str
    path: Optional[str]
    description: str
    public: bool
