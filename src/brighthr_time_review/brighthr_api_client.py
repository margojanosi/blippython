"""BrightHR API client for fetching Blip (clock-in/out) attendance data.

Provides an alternative data-ingestion path to the CSV export: instead of
exporting a CSV from BrightHR and loading it via :mod:`loader`, this module
authenticates with the BrightHR Customer API using the OAuth 2.0 client-
credentials flow and fetches Blip attendance records directly for a given
date range.

The public entry point :func:`load_from_api` returns a :class:`pandas.DataFrame`
with the same internal column schema as :func:`loader.load_csv`, so the rest of
the pipeline (normalizer, rules engine, workbook builder) is unchanged.

Required environment variables
--------------------------------
BRIGHTHR_CLIENT_ID      OAuth2 client ID issued by BrightHR.
BRIGHTHR_CLIENT_SECRET  OAuth2 client secret issued by BrightHR.

Optional environment variables
--------------------------------
BRIGHTHR_BASE_URL       Base URL of the BrightHR API.
                        Defaults to ``https://api.brighthr.com``.
BRIGHTHR_TOKEN_URL      Full URL of the OAuth2 token endpoint.
                        Defaults to ``{BRIGHTHR_BASE_URL}/oauth/token``.

API field mapping
------------------
The BrightHR API response for a Blip record is expected to contain (at
minimum) the fields listed in :data:`API_FIELD_MAP`.  The left-hand key is
the JSON field name returned by the API; the right-hand value is the internal
column name used throughout the pipeline.

If BrightHR changes their API field names, update ``API_FIELD_MAP`` — no
other module needs to change.
"""

import logging
import os
from datetime import date
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
_DEFAULT_BASE_URL = "https://api.brighthr.com"

# ---------------------------------------------------------------------------
# API → internal column mapping
#
# Keys   = JSON field names returned by the BrightHR Blip attendance API.
# Values = internal column names used throughout this pipeline.
#
# Adjust the keys if BrightHR uses different field names in their responses.
# ---------------------------------------------------------------------------
API_FIELD_MAP: dict[str, str] = {
    "firstName": "first_name",
    "lastName": "last_name",
    "jobTitle": "job_title",
    "teams": "teams",
    "blipType": "blip_type",
    "clockInDate": "clock_in_date_raw",
    "clockInTime": "clock_in_time_raw",
    "clockInLocation": "clock_in_location",
    "clockOutDate": "clock_out_date_raw",
    "clockOutTime": "clock_out_time_raw",
    "clockOutLocation": "clock_out_location",
    "totalDuration": "total_duration_raw",
    "totalExcludingBreaks": "total_excl_breaks_raw",
    "notes": "notes",
    "payrollNumber": "employee_id",
    "siNumber": "si_number",
    "employeeAddress": "employee_address",
}

# Columns that MUST be present in every API record.
_REQUIRED_API_FIELDS = {"firstName", "lastName", "clockInDate"}


def _require_env(name: str) -> str:
    """Return the value of an environment variable, raising if absent/empty."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set or is empty. "
            "Set BRIGHTHR_CLIENT_ID and BRIGHTHR_CLIENT_SECRET before using --source api."
        )
    return value


def _get_access_token(
    client_id: str,
    client_secret: str,
    token_url: str,
) -> str:
    """Obtain an OAuth 2.0 access token via the client-credentials flow.

    Args:
        client_id:     BrightHR OAuth2 client ID.
        client_secret: BrightHR OAuth2 client secret.
        token_url:     Full URL of the token endpoint.

    Returns:
        A bearer access token string.

    Raises:
        RuntimeError: If the token request fails.
    """
    logger.info("Acquiring BrightHR API access token …")
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    try:
        response = requests.post(token_url, data=payload, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Network error while requesting BrightHR access token: {exc}"
        ) from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"BrightHR token request failed — HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()
    token: str | None = data.get("access_token")
    if not token:
        raise RuntimeError(
            f"BrightHR token response did not contain 'access_token'. "
            f"Response: {str(data)[:200]}"
        )

    logger.debug("Access token acquired.")
    return token


def _fetch_blip_records(
    token: str,
    date_from: date,
    date_to: date,
    base_url: str,
) -> list[dict[str, Any]]:
    """Fetch Blip attendance records from the BrightHR API.

    Handles simple pagination: if the response contains a ``nextPage`` or
    ``next`` link the function follows it until all pages are retrieved.

    Args:
        token:     OAuth2 access token string.
        date_from: Start date (inclusive).
        date_to:   End date (inclusive).
        base_url:  API base URL.

    Returns:
        List of raw record dicts from the API (all pages combined).

    Raises:
        RuntimeError: If an API call fails.
    """
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
    }
    params: dict[str, Any] = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
    }
    url: str | None = f"{base_url.rstrip('/')}/v1/blip/attendance"
    records: list[dict[str, Any]] = []

    while url:
        logger.debug("Fetching BrightHR Blip records from %s …", url)
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                f"Network error while fetching Blip attendance data: {exc}"
            ) from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"BrightHR API error — HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        body: dict[str, Any] = response.json()

        # Support both a bare list response and a paginated envelope.
        if isinstance(body, list):
            records.extend(body)
            url = None
        elif isinstance(body, dict):
            page_data = body.get("data") or body.get("records") or body.get("items") or []
            records.extend(page_data)
            # Follow pagination links if present
            url = body.get("nextPage") or body.get("next")
        else:
            raise RuntimeError(
                f"Unexpected BrightHR API response shape: {type(body)}"
            )

        # After the first request params are encoded in the nextPage URL itself
        params = {}

    logger.info("Fetched %d Blip record(s) from BrightHR API.", len(records))
    return records


def _records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of raw API records into an internal-schema DataFrame.

    Maps API field names to internal column names via :data:`API_FIELD_MAP`,
    adds the ``source_row`` column, and fills any absent mapped columns with
    empty strings (so downstream code can rely on every expected column being
    present).

    Args:
        records: Raw record dicts from the BrightHR API.

    Returns:
        DataFrame with internal column schema (same as :func:`loader.load_csv`).

    Raises:
        ValueError: If a required API field is missing from every record.
    """
    if not records:
        # Return an empty DataFrame with the expected columns
        internal_cols = ["source_row"] + list(API_FIELD_MAP.values())
        return pd.DataFrame(columns=internal_cols)

    # Validate that required fields appear in at least the first record
    first = records[0]
    missing = _REQUIRED_API_FIELDS - set(first.keys())
    if missing:
        raise ValueError(
            f"BrightHR API response records are missing required fields: {missing}. "
            f"Received fields: {list(first.keys())}"
        )

    # Build rows using only the mapped fields
    rows: list[dict[str, Any]] = []
    for idx, rec in enumerate(records, start=1):
        row: dict[str, Any] = {"source_row": idx}
        for api_field, internal_name in API_FIELD_MAP.items():
            raw = rec.get(api_field, "")
            # Normalise lists (e.g. teams) to a comma-and-space-separated string
            if isinstance(raw, list):
                raw = ", ".join(str(v) for v in raw)
            row[internal_name] = str(raw) if raw is not None else ""
        rows.append(row)

    df = pd.DataFrame(rows)
    logger.debug("Converted %d API record(s) to DataFrame.", len(df))
    return df


def load_from_api(
    date_from: date,
    date_to: date,
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    base_url: str | None = None,
    token_url: str | None = None,
) -> pd.DataFrame:
    """Fetch BrightHR Blip attendance data and return it as an internal DataFrame.

    This is a drop-in alternative to :func:`loader.load_csv`.  The returned
    DataFrame has the same column schema so the rest of the pipeline
    (normalizer, rules engine, workbook builder) is unchanged.

    Credentials are read from environment variables by default:
    ``BRIGHTHR_CLIENT_ID`` and ``BRIGHTHR_CLIENT_SECRET``.

    Args:
        date_from:     Start of the date range to fetch (inclusive).
        date_to:       End of the date range to fetch (inclusive).
        client_id:     Override for the OAuth2 client ID (defaults to env var).
        client_secret: Override for the OAuth2 client secret (defaults to env var).
        base_url:      API base URL (defaults to env var or ``_DEFAULT_BASE_URL``).
        token_url:     OAuth2 token endpoint URL (defaults to
                       ``{base_url}/oauth/token``).

    Returns:
        DataFrame with internal column names, equivalent to the output of
        :func:`loader.load_csv`.

    Raises:
        EnvironmentError: If required credentials are not supplied.
        ValueError:       If ``date_from`` is after ``date_to``, or if the API
                          response is missing required fields.
        RuntimeError:     If authentication or the API call fails.
    """
    if date_from > date_to:
        raise ValueError(
            f"date_from ({date_from}) must not be after date_to ({date_to})."
        )

    # Resolve credentials and URLs
    resolved_client_id = client_id or _require_env("BRIGHTHR_CLIENT_ID")
    resolved_client_secret = client_secret or _require_env("BRIGHTHR_CLIENT_SECRET")
    resolved_base_url = (
        base_url
        or os.environ.get("BRIGHTHR_BASE_URL", "").strip()
        or _DEFAULT_BASE_URL
    )
    resolved_token_url = (
        token_url
        or os.environ.get("BRIGHTHR_TOKEN_URL", "").strip()
        or f"{resolved_base_url.rstrip('/')}/oauth/token"
    )

    logger.info(
        "Fetching BrightHR Blip data via API for %s → %s …",
        date_from.isoformat(),
        date_to.isoformat(),
    )

    token = _get_access_token(resolved_client_id, resolved_client_secret, resolved_token_url)
    records = _fetch_blip_records(token, date_from, date_to, resolved_base_url)
    df = _records_to_dataframe(records)

    logger.info(
        "Loaded %d row(s) from BrightHR API (%s → %s).",
        len(df),
        date_from.isoformat(),
        date_to.isoformat(),
    )
    return df
