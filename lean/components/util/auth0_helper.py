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

from lean.models.api import QCAuth0Authorization
from lean.components.api.api_client import Auth0Client
from lean.components.util.logger import Logger


def get_authorization(auth0_client: Auth0Client, brokerage_id: str, logger: Logger, project_id: int) -> QCAuth0Authorization:
    """Gets the authorization data for a brokerage, authorizing if necessary.

    :param auth0_client: An instance of Auth0Client, containing methods to interact with live/auth0/* API endpoints.
    :param brokerage_id: The ID of the brokerage to get the authorization data for.
    :param logger: An instance of Logger, handling all output printing.
    :param project_id: The local or cloud project_id.
    :return: The authorization data for the specified brokerage.
    """
    from time import time, sleep

    data = auth0_client.read(brokerage_id)
    if data.authorization is not None:
        return data

    start_time = time()
    auth0_client.authorize(brokerage_id, logger, project_id)

    # keep checking for new data every 5 seconds for 7 minutes
    while time() - start_time < 420:
        logger.info("Will sleep 5 seconds and retry fetching authorization...")
        sleep(5)
        data = auth0_client.read(brokerage_id)
        if data.authorization is None:
            continue
        return data

    raise Exception("Authorization failed")
