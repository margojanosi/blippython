"""Tests for the BrightHR API client module."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from brighthr_time_review.brighthr_api_client import (
    API_FIELD_MAP,
    _get_access_token,
    _fetch_blip_records,
    _records_to_dataframe,
    _require_env,
    load_from_api,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_SAMPLE_RECORDS = [
    {
        "firstName": "Alex",
        "lastName": "Green",
        "jobTitle": "Advisor",
        "teams": ["Support"],
        "blipType": "Clocked",
        "clockInDate": "2026-06-30",
        "clockInTime": "09:00",
        "clockInLocation": "HQ",
        "clockOutDate": "2026-06-30",
        "clockOutTime": "17:30",
        "clockOutLocation": "HQ",
        "totalDuration": "8:30",
        "totalExcludingBreaks": "8:00",
        "notes": "",
        "payrollNumber": "E100",
        "siNumber": "SI100",
        "employeeAddress": "1 Demo Street",
    },
    {
        "firstName": "Bailey",
        "lastName": "Stone",
        "jobTitle": "Advisor",
        "teams": ["Support"],
        "blipType": "Clocked",
        "clockInDate": "2026-06-30",
        "clockInTime": "09:00",
        "clockInLocation": "HQ",
        "clockOutDate": "",
        "clockOutTime": "",
        "clockOutLocation": "",
        "totalDuration": "",
        "totalExcludingBreaks": "",
        "notes": "Missing clock out",
        "payrollNumber": "E101",
        "siNumber": "SI101",
        "employeeAddress": "2 Demo Street",
    },
]


# ---------------------------------------------------------------------------
# _require_env
# ---------------------------------------------------------------------------


def test_require_env_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIGHTHR_TEST_VAR", "hello")
    assert _require_env("BRIGHTHR_TEST_VAR") == "hello"


def test_require_env_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIGHTHR_TEST_VAR", "  value  ")
    assert _require_env("BRIGHTHR_TEST_VAR") == "value"


def test_require_env_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRIGHTHR_MISSING_VAR", raising=False)
    with pytest.raises(EnvironmentError, match="BRIGHTHR_MISSING_VAR"):
        _require_env("BRIGHTHR_MISSING_VAR")


def test_require_env_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIGHTHR_EMPTY_VAR", "   ")
    with pytest.raises(EnvironmentError, match="BRIGHTHR_EMPTY_VAR"):
        _require_env("BRIGHTHR_EMPTY_VAR")


# ---------------------------------------------------------------------------
# _get_access_token
# ---------------------------------------------------------------------------


def _make_token_response(status: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.text = str(body)
    return resp


def test_get_access_token_success() -> None:
    mock_resp = _make_token_response(200, {"access_token": "tok-abc"})
    with patch("brighthr_time_review.brighthr_api_client.requests.post", return_value=mock_resp):
        token = _get_access_token("client-id", "secret", "https://api.brighthr.com/oauth/token")
    assert token == "tok-abc"


def test_get_access_token_http_error() -> None:
    mock_resp = _make_token_response(401, {"error": "invalid_client"})
    with patch("brighthr_time_review.brighthr_api_client.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="HTTP 401"):
            _get_access_token("bad-id", "bad-secret", "https://api.brighthr.com/oauth/token")


def test_get_access_token_missing_in_response() -> None:
    mock_resp = _make_token_response(200, {"token_type": "bearer"})
    with patch("brighthr_time_review.brighthr_api_client.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="access_token"):
            _get_access_token("id", "secret", "https://api.brighthr.com/oauth/token")


def test_get_access_token_network_error() -> None:
    with patch(
        "brighthr_time_review.brighthr_api_client.requests.post",
        side_effect=requests.exceptions.ConnectionError("refused"),
    ):
        with pytest.raises(RuntimeError, match="Network error"):
            _get_access_token("id", "secret", "https://api.brighthr.com/oauth/token")


# ---------------------------------------------------------------------------
# _fetch_blip_records
# ---------------------------------------------------------------------------


def _make_api_response(status: int, body) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.text = str(body)
    return resp


def test_fetch_blip_records_list_response() -> None:
    """API returns a bare list."""
    mock_resp = _make_api_response(200, _SAMPLE_RECORDS)
    with patch("brighthr_time_review.brighthr_api_client.requests.get", return_value=mock_resp):
        records = _fetch_blip_records("tok", date(2026, 6, 1), date(2026, 6, 30), "https://api.brighthr.com")
    assert len(records) == 2
    assert records[0]["firstName"] == "Alex"


def test_fetch_blip_records_envelope_response() -> None:
    """API returns paginated envelope with 'data' key."""
    mock_resp = _make_api_response(200, {"data": _SAMPLE_RECORDS, "nextPage": None})
    with patch("brighthr_time_review.brighthr_api_client.requests.get", return_value=mock_resp):
        records = _fetch_blip_records("tok", date(2026, 6, 1), date(2026, 6, 30), "https://api.brighthr.com")
    assert len(records) == 2


def test_fetch_blip_records_pagination() -> None:
    """Follows nextPage link across two pages."""
    page1 = {"data": [_SAMPLE_RECORDS[0]], "nextPage": "https://api.brighthr.com/v1/blip/attendance?page=2"}
    page2 = {"data": [_SAMPLE_RECORDS[1]], "nextPage": None}

    responses = [_make_api_response(200, page1), _make_api_response(200, page2)]
    with patch("brighthr_time_review.brighthr_api_client.requests.get", side_effect=responses):
        records = _fetch_blip_records("tok", date(2026, 6, 1), date(2026, 6, 30), "https://api.brighthr.com")
    assert len(records) == 2


def test_fetch_blip_records_http_error() -> None:
    mock_resp = _make_api_response(403, {"error": "forbidden"})
    with patch("brighthr_time_review.brighthr_api_client.requests.get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="HTTP 403"):
            _fetch_blip_records("tok", date(2026, 6, 1), date(2026, 6, 30), "https://api.brighthr.com")


def test_fetch_blip_records_network_error() -> None:
    with patch(
        "brighthr_time_review.brighthr_api_client.requests.get",
        side_effect=requests.exceptions.ConnectionError("timeout"),
    ):
        with pytest.raises(RuntimeError, match="Network error"):
            _fetch_blip_records("tok", date(2026, 6, 1), date(2026, 6, 30), "https://api.brighthr.com")


# ---------------------------------------------------------------------------
# _records_to_dataframe
# ---------------------------------------------------------------------------


def test_records_to_dataframe_returns_dataframe() -> None:
    df = _records_to_dataframe(_SAMPLE_RECORDS)
    assert isinstance(df, pd.DataFrame)


def test_records_to_dataframe_row_count() -> None:
    df = _records_to_dataframe(_SAMPLE_RECORDS)
    assert len(df) == 2


def test_records_to_dataframe_source_row_column() -> None:
    df = _records_to_dataframe(_SAMPLE_RECORDS)
    assert "source_row" in df.columns
    assert list(df["source_row"]) == [1, 2]


def test_records_to_dataframe_internal_column_names() -> None:
    df = _records_to_dataframe(_SAMPLE_RECORDS)
    for internal_col in API_FIELD_MAP.values():
        assert internal_col in df.columns, f"Missing column: {internal_col}"


def test_records_to_dataframe_maps_values() -> None:
    df = _records_to_dataframe(_SAMPLE_RECORDS)
    assert df.iloc[0]["first_name"] == "Alex"
    assert df.iloc[0]["last_name"] == "Green"
    assert df.iloc[0]["clock_in_date_raw"] == "2026-06-30"
    assert df.iloc[0]["clock_in_time_raw"] == "09:00"


def test_records_to_dataframe_normalises_list_fields() -> None:
    """List values (e.g. teams) should be joined to a comma-separated string."""
    df = _records_to_dataframe(_SAMPLE_RECORDS)
    assert df.iloc[0]["teams"] == "Support"


def test_records_to_dataframe_empty_returns_schema() -> None:
    df = _records_to_dataframe([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert "source_row" in df.columns
    for col in API_FIELD_MAP.values():
        assert col in df.columns


def test_records_to_dataframe_missing_required_field() -> None:
    bad_records = [{"firstName": "X"}]  # missing lastName and clockInDate
    with pytest.raises(ValueError, match="missing required fields"):
        _records_to_dataframe(bad_records)


# ---------------------------------------------------------------------------
# load_from_api (integration of all steps)
# ---------------------------------------------------------------------------


def test_load_from_api_date_validation() -> None:
    with pytest.raises(ValueError, match="date_from"):
        load_from_api(date(2026, 7, 1), date(2026, 6, 1), client_id="x", client_secret="y")


def test_load_from_api_missing_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRIGHTHR_CLIENT_ID", raising=False)
    with pytest.raises(EnvironmentError, match="BRIGHTHR_CLIENT_ID"):
        load_from_api(date(2026, 6, 1), date(2026, 6, 30))


def test_load_from_api_missing_client_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIGHTHR_CLIENT_ID", "some-id")
    monkeypatch.delenv("BRIGHTHR_CLIENT_SECRET", raising=False)
    with pytest.raises(EnvironmentError, match="BRIGHTHR_CLIENT_SECRET"):
        load_from_api(date(2026, 6, 1), date(2026, 6, 30))


def test_load_from_api_returns_dataframe() -> None:
    with patch(
        "brighthr_time_review.brighthr_api_client._get_access_token",
        return_value="tok",
    ), patch(
        "brighthr_time_review.brighthr_api_client._fetch_blip_records",
        return_value=_SAMPLE_RECORDS,
    ):
        df = load_from_api(
            date(2026, 6, 1),
            date(2026, 6, 30),
            client_id="id",
            client_secret="secret",
        )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "first_name" in df.columns
    assert "clock_in_date_raw" in df.columns


def test_load_from_api_uses_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIGHTHR_CLIENT_ID", "env-id")
    monkeypatch.setenv("BRIGHTHR_CLIENT_SECRET", "env-secret")
    monkeypatch.setenv("BRIGHTHR_BASE_URL", "https://api.example.com")

    with patch(
        "brighthr_time_review.brighthr_api_client._get_access_token",
        return_value="tok",
    ) as mock_token, patch(
        "brighthr_time_review.brighthr_api_client._fetch_blip_records",
        return_value=[],
    ):
        load_from_api(date(2026, 6, 1), date(2026, 6, 30))

    call_args = mock_token.call_args
    assert call_args[0][0] == "env-id"
    assert call_args[0][1] == "env-secret"
    assert call_args[0][2] == "https://api.example.com/oauth/token"


def test_load_from_api_custom_token_url() -> None:
    custom_token_url = "https://auth.example.com/token"
    with patch(
        "brighthr_time_review.brighthr_api_client._get_access_token",
        return_value="tok",
    ) as mock_token, patch(
        "brighthr_time_review.brighthr_api_client._fetch_blip_records",
        return_value=[],
    ):
        load_from_api(
            date(2026, 6, 1),
            date(2026, 6, 30),
            client_id="id",
            client_secret="sec",
            token_url=custom_token_url,
        )

    assert mock_token.call_args[0][2] == custom_token_url
