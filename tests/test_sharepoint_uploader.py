"""Tests for the SharePoint uploader module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from brighthr_time_review.sharepoint_uploader import (
    _acquire_token,
    _require_env,
    _SCOPE,
    upload_to_sharepoint,
)

# ---------------------------------------------------------------------------
# _require_env
# ---------------------------------------------------------------------------


def test_require_env_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VAR_XYZ", "hello")
    assert _require_env("TEST_VAR_XYZ") == "hello"


def test_require_env_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VAR_XYZ", "  value  ")
    assert _require_env("TEST_VAR_XYZ") == "value"


def test_require_env_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_VAR_MISSING", raising=False)
    with pytest.raises(EnvironmentError, match="TEST_VAR_MISSING"):
        _require_env("TEST_VAR_MISSING")


def test_require_env_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VAR_EMPTY", "   ")
    with pytest.raises(EnvironmentError, match="TEST_VAR_EMPTY"):
        _require_env("TEST_VAR_EMPTY")


# ---------------------------------------------------------------------------
# _acquire_token
# ---------------------------------------------------------------------------


def test_acquire_token_returns_token() -> None:
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "tok123"}

    with patch("brighthr_time_review.sharepoint_uploader.msal.ConfidentialClientApplication",
               return_value=mock_app):
        token = _acquire_token("tenant-id", "client-id", "secret")

    assert token == "tok123"
    mock_app.acquire_token_for_client.assert_called_once_with(scopes=_SCOPE)


def test_acquire_token_raises_on_failure() -> None:
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "bad secret",
    }

    with patch("brighthr_time_review.sharepoint_uploader.msal.ConfidentialClientApplication",
               return_value=mock_app):
        with pytest.raises(RuntimeError, match="invalid_client"):
            _acquire_token("tenant-id", "client-id", "wrong-secret")


# ---------------------------------------------------------------------------
# upload_to_sharepoint
# ---------------------------------------------------------------------------

_SP_ENV = {
    "SHAREPOINT_TENANT_ID": "tenant-123",
    "SHAREPOINT_CLIENT_ID": "client-456",
    "SHAREPOINT_CLIENT_SECRET": "secret-789",
    "SHAREPOINT_SITE_ID": "site-abc",
    "SHAREPOINT_DRIVE_ID": "drive-def",
    "SHAREPOINT_FOLDER_PATH": "BrightHR Reviews",
}


def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, val in _SP_ENV.items():
        monkeypatch.setenv(key, val)


def test_upload_raises_when_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_env(monkeypatch)
    with pytest.raises(FileNotFoundError):
        upload_to_sharepoint(tmp_path / "nonexistent.xlsx")


def test_upload_raises_when_env_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for key in _SP_ENV:
        monkeypatch.delenv(key, raising=False)
    dummy = tmp_path / "workbook.xlsx"
    dummy.write_bytes(b"PK\x03\x04")  # minimal non-empty file
    with pytest.raises(EnvironmentError):
        upload_to_sharepoint(dummy)


def test_upload_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_env(monkeypatch)
    dummy = tmp_path / "workbook.xlsx"
    dummy.write_bytes(b"PK\x03\x04dummy xlsx content")

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "webUrl": "https://contoso.sharepoint.com/sites/hr/BrightHR%20Reviews/workbook.xlsx"
    }

    with patch("brighthr_time_review.sharepoint_uploader._acquire_token",
               return_value="mock-token"), \
         patch("brighthr_time_review.sharepoint_uploader.requests.put",
               return_value=mock_response) as mock_put:
        result = upload_to_sharepoint(dummy)

    assert result == "https://contoso.sharepoint.com/sites/hr/BrightHR%20Reviews/workbook.xlsx"
    # Verify the PUT was called with the right URL structure
    call_url = mock_put.call_args[0][0]
    assert "BrightHR Reviews" in call_url
    assert dummy.name in call_url


def test_upload_uses_custom_filename(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_env(monkeypatch)
    dummy = tmp_path / "local_name.xlsx"
    dummy.write_bytes(b"PK\x03\x04dummy")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"webUrl": "https://example.com/custom.xlsx"}

    with patch("brighthr_time_review.sharepoint_uploader._acquire_token",
               return_value="mock-token"), \
         patch("brighthr_time_review.sharepoint_uploader.requests.put",
               return_value=mock_response) as mock_put:
        result = upload_to_sharepoint(dummy, filename="custom.xlsx")

    call_url = mock_put.call_args[0][0]
    assert "custom.xlsx" in call_url
    assert "local_name.xlsx" not in call_url


def test_upload_raises_on_http_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_env(monkeypatch)
    dummy = tmp_path / "workbook.xlsx"
    dummy.write_bytes(b"PK\x03\x04dummy")

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Access denied"

    with patch("brighthr_time_review.sharepoint_uploader._acquire_token",
               return_value="mock-token"), \
         patch("brighthr_time_review.sharepoint_uploader.requests.put",
               return_value=mock_response):
        with pytest.raises(RuntimeError, match="HTTP 403"):
            upload_to_sharepoint(dummy)


def test_upload_raises_on_network_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_env(monkeypatch)
    dummy = tmp_path / "workbook.xlsx"
    dummy.write_bytes(b"PK\x03\x04dummy")

    with patch("brighthr_time_review.sharepoint_uploader._acquire_token",
               return_value="mock-token"), \
         patch("brighthr_time_review.sharepoint_uploader.requests.put",
               side_effect=requests.exceptions.ConnectionError("connection refused")):
        with pytest.raises(RuntimeError, match="Network error"):
            upload_to_sharepoint(dummy)


def test_upload_root_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When SHAREPOINT_FOLDER_PATH is empty the file goes to the drive root."""
    _set_env(monkeypatch)
    monkeypatch.setenv("SHAREPOINT_FOLDER_PATH", "")
    dummy = tmp_path / "root.xlsx"
    dummy.write_bytes(b"PK\x03\x04dummy")

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"webUrl": "https://example.com/root.xlsx"}

    with patch("brighthr_time_review.sharepoint_uploader._acquire_token",
               return_value="mock-token"), \
         patch("brighthr_time_review.sharepoint_uploader.requests.put",
               return_value=mock_response) as mock_put:
        upload_to_sharepoint(dummy)

    call_url = mock_put.call_args[0][0]
    # Should be root:/root.xlsx:/content — no folder prefix
    assert "/root:/root.xlsx:/content" in call_url
