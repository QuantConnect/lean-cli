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
from typing import Optional

from click import command, option, prompt

from lean.click import LeanCommand
from lean.container import container
from lean.constants import GHCR_ENGINE_IMAGE, GHCR_RESEARCH_IMAGE, GHCR_REGISTRY


@command(cls=LeanCommand)
@option("--user-id", "-U", type=str, help="QuantConnect user ID (numeric, defaults to '0')")
@option("--url", "-u", type=str, help="Data server URL")
@option("--api-key", "-k", type=str, help="API key for data server")
@option("--thetadata-url", "-t", type=str, help="ThetaData REST API URL")
@option("--thetadata-api-key", "-T", type=str, help="ThetaData API key (Bearer token)")
@option("--ghcr-token", "-g", type=str, help="GitHub Container Registry token for private LEAN images")
@option("--kalshi-api-key", type=str, help="Kalshi API key")
@option("--kalshi-private-key", type=str, help="Kalshi private key (or path to key file)")
@option("--tradealert-s3-access-key", type=str, help="TradeAlert S3 access key")
@option("--tradealert-s3-secret-key", type=str, help="TradeAlert S3 secret key")
@option("--show-secrets", is_flag=True, show_default=True, default=False, help="Show secrets as they are input")
def login(user_id: Optional[str],
          url: Optional[str],
          api_key: Optional[str],
          thetadata_url: Optional[str],
          thetadata_api_key: Optional[str],
          ghcr_token: Optional[str],
          kalshi_api_key: Optional[str],
          kalshi_private_key: Optional[str],
          tradealert_s3_access_key: Optional[str],
          tradealert_s3_secret_key: Optional[str],
          show_secrets: bool) -> None:
    """Log in to the data server, configure ThetaData, and authenticate with the private container registry.

    If URL or API key is not provided an interactive prompt will show.

    Credentials are stored in ~/.lean/credentials and are removed upon running `lean logout`.
    """
    logger = container.logger
    cli_config_manager = container.cli_config_manager

    # Set default user-id if not already set
    # Note: user-id must be numeric as LEAN expects an integer for job-user-id
    current_user_id = cli_config_manager.user_id.get_value()
    if user_id is None:
        # Ensure we use a numeric value (fix any non-numeric stored values)
        if current_user_id and current_user_id.isdigit():
            user_id = current_user_id
        else:
            user_id = "0"
    cli_config_manager.user_id.set_value(user_id)

    # Set a placeholder API token if not already set (needed to avoid validation errors)
    current_api_token = cli_config_manager.api_token.get_value()
    if current_api_token is None:
        cli_config_manager.api_token.set_value("placeholder")

    current_url = cli_config_manager.data_server_url.get_value() if hasattr(cli_config_manager, 'data_server_url') else None
    current_api_key = cli_config_manager.data_server_api_key.get_value() if hasattr(cli_config_manager, 'data_server_api_key') else None

    if url is None:
        url = prompt("Data server URL", default=current_url or "http://0.0.0.0:5067")

    if api_key is None:
        api_key = logger.prompt_password("API key", current_api_key, hide_input=not show_secrets)

    cli_config_manager.data_server_url.set_value(url)
    cli_config_manager.data_server_api_key.set_value(api_key)

    logger.info(f"Successfully configured data server: {url}")

    # ThetaData configuration
    current_thetadata_url = cli_config_manager.thetadata_url.get_value()
    current_thetadata_api_key = cli_config_manager.thetadata_api_key.get_value()

    if thetadata_url is None:
        thetadata_url = prompt("ThetaData REST API URL", default=current_thetadata_url or "https://thetadata.cascadelabs.io")

    if thetadata_api_key is None:
        thetadata_api_key = logger.prompt_password("ThetaData API key", current_thetadata_api_key, hide_input=not show_secrets)

    cli_config_manager.thetadata_url.set_value(thetadata_url)
    cli_config_manager.thetadata_api_key.set_value(thetadata_api_key)

    logger.info(f"Successfully configured ThetaData: {thetadata_url}")

    # GHCR configuration for private LEAN images
    current_ghcr_token = cli_config_manager.ghcr_token.get_value()

    if ghcr_token is None:
        logger.info("")
        logger.info("A GitHub Personal Access Token is required to pull the private LEAN engine images.")
        logger.info("To create one: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)")
        logger.info("Or visit: https://github.com/settings/tokens")
        logger.info("Required scope: read:packages")
        logger.info("")
        ghcr_token = logger.prompt_password("GitHub Container Registry token", current_ghcr_token, hide_input=not show_secrets)

    cli_config_manager.ghcr_token.set_value(ghcr_token)

    # Authenticate with GHCR
    docker_manager = container.docker_manager
    docker_manager.login_registry(GHCR_REGISTRY, "ghcr", ghcr_token)

    # Set the engine and research images to use the private registry
    cli_config_manager.engine_image.set_value(GHCR_ENGINE_IMAGE)
    cli_config_manager.research_image.set_value(GHCR_RESEARCH_IMAGE)

    logger.info(f"Successfully configured private container registry")
    logger.info(f"Engine image: {GHCR_ENGINE_IMAGE}")
    logger.info(f"Research image: {GHCR_RESEARCH_IMAGE}")

    # Kalshi credentials (optional)
    current_kalshi_api_key = cli_config_manager.kalshi_api_key.get_value()
    current_kalshi_private_key = cli_config_manager.kalshi_private_key.get_value()

    if kalshi_api_key is None:
        logger.info("")
        logger.info("Kalshi API key (press Enter to skip):")
        kalshi_api_key = logger.prompt_password("Kalshi API key", current_kalshi_api_key, hide_input=not show_secrets, allow_empty=True)

    if kalshi_api_key:
        cli_config_manager.kalshi_api_key.set_value(kalshi_api_key)

        if kalshi_private_key is None:
            logger.info("Kalshi private key - enter path to key file or paste key directly (press Enter to skip):")
            kalshi_private_key = logger.prompt_password("Kalshi private key", current_kalshi_private_key, hide_input=not show_secrets, allow_empty=True)

        if kalshi_private_key:
            # Check if input is a file path
            key_path = Path(kalshi_private_key).expanduser()
            if key_path.exists() and key_path.is_file():
                kalshi_private_key = key_path.read_text(encoding="utf-8").strip()
                logger.info(f"Loaded private key from {key_path}")

            cli_config_manager.kalshi_private_key.set_value(kalshi_private_key)

        logger.info("Successfully configured Kalshi credentials")

    # TradeAlert S3 credentials (optional)
    current_s3_access_key = cli_config_manager.tradealert_s3_access_key.get_value()
    current_s3_secret_key = cli_config_manager.tradealert_s3_secret_key.get_value()

    if tradealert_s3_access_key is None:
        logger.info("")
        logger.info("TradeAlert S3 access key (press Enter to skip):")
        tradealert_s3_access_key = logger.prompt_password("TradeAlert S3 access key", current_s3_access_key, hide_input=not show_secrets, allow_empty=True)

    if tradealert_s3_access_key:
        cli_config_manager.tradealert_s3_access_key.set_value(tradealert_s3_access_key)

        if tradealert_s3_secret_key is None:
            tradealert_s3_secret_key = logger.prompt_password("TradeAlert S3 secret key", current_s3_secret_key, hide_input=not show_secrets, allow_empty=True)

        if tradealert_s3_secret_key:
            cli_config_manager.tradealert_s3_secret_key.set_value(tradealert_s3_secret_key)

        # Set TradeAlert S3 defaults
        cli_config_manager.tradealert_s3_endpoint.set_value("tradealert-idvfareebwfp.private.compat.objectstorage.us-ashburn-1.oci.customer-oci.com")
        cli_config_manager.tradealert_s3_bucket.set_value("trade_alert")
        cli_config_manager.tradealert_s3_region.set_value("us-ashburn-1")

        logger.info("Successfully configured TradeAlert S3 credentials")
