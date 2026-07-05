"""Tests for the data normalizer module."""

import textwrap
from pathlib import Path

import pandas as pd
import pytest

from brighthr_time_review.loader import load_csv
from brighthr_time_review.normalizer import normalize


@pytest.fixture()
def full_sample_df() -> pd.DataFrame:
    sample = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "input"
        / "sample_bright_hr_export.csv"
    )
    return load_csv(sample)


def _make_raw_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal raw DataFrame for normalizer tests."""
    base = {
        "source_row": 1,
        "employee_name": "Test Employee",
        "employee_id": "EMP001",
        "work_date_raw": "2024-06-03",
        "clock_in_raw": "09:00",
        "clock_out_raw": "17:00",
        "break_start_raw": "12:00",
        "break_end_raw": "12:30",
        "break_minutes_raw": "30",
        "location": "Office",
        "notes": "",
    }
    records = []
    for i, row in enumerate(rows):
        r = {**base, "source_row": i + 1, **row}
        records.append(r)
    return pd.DataFrame(records)


def test_normalize_returns_dataframe(full_sample_df: pd.DataFrame) -> None:
    result = normalize(full_sample_df)
    assert isinstance(result, pd.DataFrame)


def test_normalize_row_count_matches(full_sample_df: pd.DataFrame) -> None:
    result = normalize(full_sample_df)
    assert len(result) == len(full_sample_df)


def test_normalize_calculated_columns_present(full_sample_df: pd.DataFrame) -> None:
    result = normalize(full_sample_df)
    required_cols = [
        "work_date",
        "day_of_week",
        "is_weekend",
        "clock_in",
        "clock_out",
        "calc_shift_hours",
        "calc_break_minutes",
        "calc_paid_hours",
        "has_clock_in",
        "has_clock_out",
        "has_break",
        "normalization_warnings",
    ]
    for col in required_cols:
        assert col in result.columns, f"Missing column: {col}"


def test_normalize_clean_record_shift_hours() -> None:
    df = _make_raw_df([{"clock_in_raw": "08:00", "clock_out_raw": "16:00"}])
    result = normalize(df)
    assert result.iloc[0]["calc_shift_hours"] == pytest.approx(8.0)


def test_normalize_clean_record_break_minutes() -> None:
    df = _make_raw_df([{"break_start_raw": "12:00", "break_end_raw": "12:30"}])
    result = normalize(df)
    assert result.iloc[0]["calc_break_minutes"] == pytest.approx(30.0)


def test_normalize_paid_hours_deducts_break() -> None:
    df = _make_raw_df(
        [{"clock_in_raw": "08:00", "clock_out_raw": "16:00",
          "break_start_raw": "12:00", "break_end_raw": "12:30"}]
    )
    result = normalize(df)
    # 8 hours shift - 0.5 hours break = 7.5 paid
    assert result.iloc[0]["calc_paid_hours"] == pytest.approx(7.5)


def test_normalize_missing_clock_out_flags() -> None:
    df = _make_raw_df([{"clock_out_raw": ""}])
    result = normalize(df)
    assert not result.iloc[0]["has_clock_out"]


def test_normalize_missing_clock_in_flags() -> None:
    df = _make_raw_df([{"clock_in_raw": ""}])
    result = normalize(df)
    assert not result.iloc[0]["has_clock_in"]


def test_normalize_weekend_detection() -> None:
    # 2024-06-08 is a Saturday
    df = _make_raw_df([{"work_date_raw": "2024-06-08"}])
    result = normalize(df)
    assert result.iloc[0]["is_weekend"]
    assert result.iloc[0]["day_of_week"] == "Saturday"


def test_normalize_weekday_not_flagged_as_weekend() -> None:
    # 2024-06-03 is a Monday
    df = _make_raw_df([{"work_date_raw": "2024-06-03"}])
    result = normalize(df)
    assert not result.iloc[0]["is_weekend"]


def test_normalize_no_warnings_for_clean_record() -> None:
    df = _make_raw_df([{}])
    result = normalize(df)
    assert result.iloc[0]["normalization_warnings"] == ""


def test_normalize_bad_date_produces_warning() -> None:
    df = _make_raw_df([{"work_date_raw": "not-a-date"}])
    result = normalize(df)
    assert "Work Date" in result.iloc[0]["normalization_warnings"]


def test_normalize_break_minutes_from_raw_when_no_times() -> None:
    """If break times are blank but break_minutes_raw is set, use that."""
    df = _make_raw_df(
        [{"break_start_raw": "", "break_end_raw": "", "break_minutes_raw": "45"}]
    )
    result = normalize(df)
    assert result.iloc[0]["calc_break_minutes"] == pytest.approx(45.0)
