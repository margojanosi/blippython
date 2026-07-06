"""SharePoint uploader for BrightHR Time Review workbooks.

Uses MSAL for Azure AD authentication and the Microsoft Graph API to upload
the generated Excel workbook directly to a SharePoint document library, so
it never needs to be exposed as a public GitHub Actions artifact.

Required environment variables
-------------------------------
SHAREPOINT_TENANT_ID      Azure AD tenant ID (GUID).
SHAREPOINT_CLIENT_ID      Azure AD app registration client ID (GUID).
SHAREPOINT_CLIENT_SECRET  Client secret value created for the app registration.
SHAREPOINT_SITE_ID        SharePoint site ID (GUID or hostname:path form accepted
                          by the Graph API).
SHAREPOINT_DRIVE_ID       Document library drive ID (GUID).
SHAREPOINT_FOLDER_PATH    Destination folder path inside the drive, e.g.
                          "BrightHR Reviews" or "Payroll/Time Reviews".
                          Use "" or "/" for the drive root.
"""

import logging
import os
from pathlib import Path

import msal
import requests

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_SCOPE = ["https://graph.microsoft.com/.default"]

_ENV_VARS = (
    "SHAREPOINT_TENANT_ID",
    "SHAREPOINT_CLIENT_ID",
    "SHAREPOINT_CLIENT_SECRET",
    "SHAREPOINT_SITE_ID",
    "SHAREPOINT_DRIVE_ID",
    "SHAREPOINT_FOLDER_PATH",
)


def _require_env(name: str) -> str:
    """Return the value of an environment variable, raising if absent/empty."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set or is empty. "
            "Set all SHAREPOINT_* variables before using --sharepoint."
        )
    return value


def _acquire_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Acquire an OAuth 2.0 access token via MSAL client-credentials flow.

    Args:
        tenant_id:     Azure AD tenant ID.
        client_id:     App registration client ID.
        client_secret: App registration client secret.

    Returns:
        A bearer access token string.

    Raises:
        RuntimeError: If MSAL cannot acquire a token.
    """
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )
    result = app.acquire_token_for_client(scopes=_SCOPE)
    if "access_token" not in result:
        error = result.get("error", "unknown")
        description = result.get("error_description", "no description")
        raise RuntimeError(
            f"MSAL failed to acquire a token. "
            f"Error: {error} — {description}"
        )
    return result["access_token"]


def upload_to_sharepoint(file_path: Path, filename: str | None = None) -> str:
    """Upload a local file to a SharePoint document library via Graph API.

    Reads all required configuration from environment variables (see module
    docstring).  The upload uses the Graph API simple-upload endpoint which
    supports files up to 4 MB — sufficient for Excel workbooks.

    Args:
        file_path: Path to the local file to upload.
        filename:  Destination filename inside the SharePoint folder.
                   Defaults to ``file_path.name``.

    Returns:
        The ``webUrl`` of the uploaded item (SharePoint link).

    Raises:
        FileNotFoundError:  If ``file_path`` does not exist.
        EnvironmentError:   If any required environment variable is missing.
        RuntimeError:       If authentication or the Graph API call fails.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File to upload not found: {file_path}")

    destination_name = filename or file_path.name

    # Read all config from environment
    tenant_id = _require_env("SHAREPOINT_TENANT_ID")
    client_id = _require_env("SHAREPOINT_CLIENT_ID")
    client_secret = _require_env("SHAREPOINT_CLIENT_SECRET")
    site_id = _require_env("SHAREPOINT_SITE_ID")
    drive_id = _require_env("SHAREPOINT_DRIVE_ID")
    folder_path = os.environ.get("SHAREPOINT_FOLDER_PATH", "").strip().strip("/")

    logger.info("Acquiring Azure AD token …")
    token = _acquire_token(tenant_id, client_id, client_secret)

    # Build the Graph API upload URL.
    # PUT /sites/{site-id}/drives/{drive-id}/root:/{folder}/{filename}:/content
    if folder_path:
        item_path = f"{folder_path}/{destination_name}"
    else:
        item_path = destination_name

    url = f"{_GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root:/{item_path}:/content"
    logger.debug("Graph API upload URL: %s", url)

    file_bytes = file_path.read_bytes()
    logger.info(
        "Uploading %s (%d bytes) to SharePoint …",
        destination_name,
        len(file_bytes),
    )

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    }

    response = requests.put(url, headers=headers, data=file_bytes, timeout=60)

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Graph API upload failed — HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    web_url: str = response.json().get("webUrl", "(URL not returned)")
    logger.info("✅  Workbook uploaded to SharePoint: %s", web_url)
    return web_url
